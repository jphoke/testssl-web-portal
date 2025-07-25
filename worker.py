from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import subprocess
import json
import os
import redis
import signal
import psutil
from datetime import datetime
from app import Scan  # Import the model
import sys
import traceback
import uuid

# Celery setup
celery_app = Celery('worker', broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ssluser:changeme@postgres:5432/ssltestportal")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client = redis.StrictRedis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

# Note: We're not using a global SIGCHLD handler as it interferes with Celery's process management
# Instead, we'll handle zombie cleanup within each task execution

def kill_process_tree(pid):
    """Kill a process tree (including grandchildren) with given pid"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # Give them time to terminate
        _, alive = psutil.wait_procs(children, timeout=3)
        
        # Force kill any remaining
        for child in alive:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        
        # Finally kill parent
        try:
            parent.terminate()
            parent.wait(timeout=3)
        except psutil.TimeoutExpired:
            parent.kill()
        except psutil.NoSuchProcess:
            pass
            
    except psutil.NoSuchProcess:
        # Process already gone
        pass
    except Exception as e:
        print(f"Error killing process tree: {e}")

@celery_app.task(name='worker.run_ssl_scan')
def run_ssl_scan(scan_id: str, host: str, port: int):
    """Run SSL scan using testssl.sh"""
    import re
    
    # Additional validation as defense in depth
    # Validate host contains only safe characters
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        print(f"Invalid host format: {host}")
        return
    
    # Validate port is in valid range
    if not isinstance(port, int) or not 1 <= port <= 65535:
        print(f"Invalid port: {port}")
        return
    
    db = SessionLocal()
    
    try:
        # Update status
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        
        scan.status = "running"
        db.commit()
        
        # Update Redis
        redis_client.set(f"scan:{scan_id}:status", "running", ex=3600)
        redis_client.set(f"scan:{scan_id}:progress", "10", ex=3600)
        
        # Run testssl.sh with comprehensive options
        testssl_path = os.getenv("TESTSSL_PATH", "/opt/testssl.sh/testssl.sh")
        
        # Ensure results directory exists
        results_dir = "/app/results"
        os.makedirs(results_dir, exist_ok=True)
        json_output = f"{results_dir}/{scan_id}.json"
        
        # More comprehensive scan command using short options
        # Note: Removed --quiet to ensure we get all output including ratings
        cmd = [
            testssl_path,
            "--jsonfile", json_output,
            "--severity", "LOW",
            "--color", "0",    # Disable colors for easier parsing
            "-p",              # --protocols: Test SSL/TLS protocols
            "-P",              # --server-preference: Server cipher preferences
            "-S",              # --server-defaults: Get server defaults
            "-h",              # --header: Security headers
            "-U",              # --vulnerable: Test all vulnerabilities
            "-s",              # --std: Test standard cipher categories
            "-f",              # --fs: Forward secrecy
            "-4",              # --rc4: RC4 ciphers
            "-W",              # --sweet32: SWEET32 vulnerability
            f"{host}:{port}"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Update progress
        redis_client.set(f"scan:{scan_id}:progress", "50", ex=3600)
        
        # Execute scan with better process management
        process = None
        stdout_data = ""
        return_code = None
        
        try:
            # Create new process group to ensure all children can be killed
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid if os.name != 'nt' else None,  # Create new process group on Unix
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0  # Windows
            )
            
            # Wait for process with timeout
            scan_timeout = int(os.getenv('SCAN_TIMEOUT', '300'))
            try:
                stdout_data, _ = process.communicate(timeout=scan_timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                print(f"Process timed out after {scan_timeout} seconds, killing process tree...")
                if os.name != 'nt':
                    # Unix: kill entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    # Windows or fallback
                    kill_process_tree(process.pid)
                
                # Get any partial output
                try:
                    stdout_data, _ = process.communicate(timeout=5)
                except:
                    stdout_data = ""
                raise subprocess.TimeoutExpired(cmd, scan_timeout, output=stdout_data)
                
        finally:
            # Ensure process is terminated
            if process and process.poll() is None:
                kill_process_tree(process.pid)
            
            # Clean up any zombie processes left by testssl.sh
            # This is done in a targeted way to avoid interfering with Celery
            try:
                # Only reap children of our process, not all zombies
                while True:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if pid == 0:
                        break
            except OSError:
                # No children to reap
                pass
        
        # Save stdout for debugging
        print(f"Scan stdout length: {len(stdout_data)}")
        if len(stdout_data) > 0:
            # Save last 1000 chars to see if rating is there
            print(f"Stdout tail: ...{stdout_data[-1000:]}")
        
        # Check for connection failures
        if return_code != 0 or "Fatal error: Can't connect to" in stdout_data or "Connection refused" in stdout_data:
            error_msg = "Unable to connect to the target host"
            if "Connection refused" in stdout_data:
                error_msg = f"Connection refused at {host}:{port}. The target is not accepting connections on this port."
            elif "Fatal error: Can't connect to" in stdout_data:
                error_msg = f"Unable to connect to {host}:{port}. Please verify the host and port are correct and accessible."
            elif "TCP connect problem" in stdout_data:
                error_msg = f"TCP connection failed to {host}:{port}. The service may be down or blocked by a firewall."
            
            # Update database with error
            scan.status = "error"
            scan.error = error_msg
            scan.completed_at = datetime.utcnow()
            db.commit()
            
            # Update Redis
            redis_client.set(f"scan:{scan_id}:status", "error", ex=3600)
            redis_client.set(f"scan:{scan_id}:progress", "100", ex=3600)
            
            # Clean up JSON file if it exists
            if os.path.exists(json_output):
                try:
                    os.remove(json_output)
                except:
                    pass
            
            return
        
        # Parse results
        results = parse_scan_results(json_output, stdout_data)
        
        # Try to extract grade from multiple sources
        grade = None
        
        # First, check if we got the grade from JSON parsing
        if results.get('summary', {}).get('grade'):
            grade = results['summary']['grade']
            print(f"Found grade '{grade}' from JSON output")
        
        # If not in JSON, try to extract from stdout
        if not grade and stdout_data:
            # Look for rating/grade in stdout - testssl.sh outputs it as "Overall Grade                A+"
            import re
            
            # Simple pattern matching now that colors are disabled
            patterns = [
                r'Overall\s+Grade\s+([A-FMT][+-]?)',  # Main pattern: "Overall Grade    A+" (includes M, T)
                r'Rating[:\s]+([A-FMT][+-]?)',
                r'Final\s+Score\s+\d+\s+.*?([A-FMT][+-]?)\s*$',
            ]
            
            for pattern in patterns:
                rating_match = re.search(pattern, stdout_data, re.IGNORECASE | re.MULTILINE)
                if rating_match:
                    grade = rating_match.group(1)
                    print(f"Found grade '{grade}' using pattern '{pattern}'")
                    break
        
        # Fall back to our calculation if still no grade
        if not grade:
            print("No grade found in JSON or stdout, calculating our own")
            grade = calculate_grade(results)
        else:
            # Normalize the grade to uppercase
            grade = grade.upper()
        
        # Update database
        scan.status = "completed"
        scan.completed_at = datetime.utcnow()
        scan.grade = grade
        scan.results = json.dumps(results)
        db.commit()
        
        # Update Redis
        redis_client.set(f"scan:{scan_id}:status", "completed", ex=3600)
        redis_client.set(f"scan:{scan_id}:progress", "100", ex=3600)
        
    except subprocess.TimeoutExpired:
        scan_timeout = int(os.getenv('SCAN_TIMEOUT', '300'))
        scan.status = "error"
        scan.error = f"Scan timeout after {scan_timeout} seconds"
        db.commit()
        # Clean up any remaining files
        if os.path.exists(json_output):
            try:
                os.remove(json_output)
            except:
                pass
    except Exception as e:
        # Generate a unique error reference ID
        error_id = str(uuid.uuid4())[:8]
        
        # Log detailed error information server-side
        print(f"Internal scan error {error_id}: {str(e)}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        
        # Store generic user-friendly message with reference ID
        scan.status = "error"
        scan.error = f"An internal error occurred during the scan (ref: {error_id}). Please try again or contact support if the issue persists."
        db.commit()
        
        # Clean up any remaining files
        if 'json_output' in locals() and os.path.exists(json_output):
            try:
                os.remove(json_output)
            except:
                pass
    finally:
        db.close()
        # Clean up Redis keys
        redis_client.delete(f"scan:{scan_id}:status")
        redis_client.delete(f"scan:{scan_id}:progress")
        # Clean up JSON output file after successful parsing
        if 'json_output' in locals() and os.path.exists(json_output):
            try:
                os.remove(json_output)
            except:
                pass

def parse_scan_results(json_file: str, stdout: str):
    """Parse testssl.sh results"""
    results = {
        "protocols": {},
        "vulnerabilities": {},
        "certificate": {},
        "ciphers": {},
        "server_defaults": {},
        "headers": {},
        "summary": {}
    }
    
    try:
        # Read JSON output
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                json_data = json.load(f)
                
            # Use a set to track processed cipher IDs to avoid duplicates
            processed_ciphers = set()
            
            for item in json_data:
                if isinstance(item, dict):
                    finding_id = item.get('id', '')
                    finding = item.get('finding', '')
                    severity = item.get('severity', 'INFO')
                    cve = item.get('cve', '')
                    
                    # Parse protocols (SSL2, SSL3, TLS1, TLS1.1, TLS1.2, TLS1.3)
                    if finding_id in ['SSLv2', 'SSLv3', 'TLS1', 'TLS1_1', 'TLS1_2', 'TLS1_3']:
                        results['protocols'][finding_id] = {
                            'name': finding_id.replace('_', '.'),
                            'supported': 'not offered' not in finding.lower() and 'offered' in finding.lower(),
                            'finding': finding
                        }
                    
                    # Parse certificate information (capture ALL cert_ fields)
                    elif finding_id.startswith('cert_'):
                        results['certificate'][finding_id] = finding
                    
                    # Parse vulnerabilities
                    elif any(vuln in finding_id for vuln in ['BEAST', 'CRIME', 'POODLE', 'SWEET32', 'FREAK', 
                                                             'DROWN', 'LOGJAM', 'ROBOT', 'heartbleed']):
                        is_vulnerable = 'not vulnerable' not in finding.lower()
                        results['vulnerabilities'][finding_id] = {
                            'severity': severity,
                            'vulnerable': is_vulnerable,
                            'finding': finding,
                            'cve': cve
                        }
                    
                    # Parse cipher information
                    elif finding_id.startswith('cipher-'):
                        # Skip if we've already processed this cipher
                        if finding_id in processed_ciphers:
                            continue
                        processed_ciphers.add(finding_id)
                        
                        # Individual cipher entry with full details
                        cipher_strength = 'strong'
                        
                        # Check severity from testssl.sh first
                        if severity in ['HIGH', 'CRITICAL']:
                            cipher_strength = 'weak'
                        elif severity in ['MEDIUM', 'LOW']:
                            cipher_strength = 'medium'
                        else:
                            # Fallback to manual classification
                            finding_lower = finding.lower()
                            # Check for weak/obsolete ciphers
                            if any(weak in finding_lower for weak in ['des-cbc3', 'rc4', 'export', 'null', 'anon', 'md5', '3des', 'idea']):
                                cipher_strength = 'weak'
                            # Check for ciphers on old protocols
                            elif 'tls1_0' in finding_id or 'tls1_1' in finding_id or 'ssl' in finding_id:
                                cipher_strength = 'weak'
                            # Check for medium strength (non-AEAD CBC ciphers)
                            elif 'cbc' in finding_lower and 'aes' in finding_lower:
                                cipher_strength = 'medium'
                            # Strong ciphers have GCM, ChaCha20, CCM, or Poly1305
                            elif any(strong in finding_lower for strong in ['gcm', 'chacha20', 'ccm', 'poly1305']):
                                cipher_strength = 'strong'
                            # Default TLS 1.2 ciphers without AEAD
                            elif 'tls1_2' in finding_id and 'cbc' not in finding_lower:
                                cipher_strength = 'medium'
                        
                        # Extract protocol from finding_id (e.g., cipher-tls1_2_x1302)
                        protocol = 'unknown'
                        if 'tls1_3' in finding_id:
                            protocol = 'TLS 1.3'
                        elif 'tls1_2' in finding_id:
                            protocol = 'TLS 1.2'
                        elif 'tls1_1' in finding_id:
                            protocol = 'TLS 1.1'
                        elif 'tls1' in finding_id:
                            protocol = 'TLS 1.0'
                        
                        if protocol not in results['ciphers']:
                            results['ciphers'][protocol] = []
                        
                        results['ciphers'][protocol].append({
                            'name': finding_id,
                            'strength': cipher_strength,
                            'details': finding,
                            'severity': severity
                        })
                    
                    # Cipher categories (e.g., cipherlist_3DES_IDEA, cipherlist_OBSOLETED)
                    elif finding_id.startswith('cipherlist_'):
                        category_name = finding_id.replace('cipherlist_', '').replace('_', ' ')
                        
                        # Determine strength based on category name and severity
                        cipher_strength = 'strong'
                        category_lower = category_name.lower()
                        
                        # Check for weak categories
                        if any(weak in category_lower for weak in ['obsoleted', 'obsolete', '3des', 'idea', 'rc4', 'export', 'null', 'anon']):
                            cipher_strength = 'weak'
                        elif severity in ['HIGH', 'CRITICAL']:
                            cipher_strength = 'weak'
                        elif severity in ['MEDIUM', 'LOW']:
                            cipher_strength = 'medium'
                        elif 'cbc' in category_lower:
                            cipher_strength = 'medium'
                        
                        if category_name not in results['ciphers']:
                            results['ciphers'][category_name] = []
                        results['ciphers'][category_name].append({
                            'name': category_name,
                            'strength': cipher_strength,
                            'details': finding,
                            'severity': severity
                        })
                    
                    # Parse server defaults
                    elif finding_id in ['TLS_session_ticket', 'SSL_sessionID_support', 'session_resumption']:
                        results['server_defaults'][finding_id] = finding
                    
                    # Parse security headers
                    elif finding_id in ['HSTS', 'HPKP', 'banner_server', 'banner_application', 
                                       'cookie_secure', 'cookie_httponly']:
                        results['headers'][finding_id] = {
                            'finding': finding,
                            'severity': severity
                        }
                    
                    # Certificate details (additional specific fields)
                    elif finding_id in ['cert_commonName', 'cert_subjectAltName', 'cert_notBefore', 
                                       'cert_notAfter', 'cert_signatureAlgorithm', 'cert_issuer',
                                       'cert_validity', 'cert_chain', 'cert_keySize', 'cert_trust',
                                       'cert_validityPeriod', 'cert_expirationStatus', 'cert_CN',
                                       'cert_SAN', 'cert_issuerDN', 'issuer', 'cn', 'san']:
                        results['certificate'][finding_id] = finding
                    
                    # Forward Secrecy
                    elif 'PFS' in finding_id or 'forward_secrecy' in finding_id:
                        results['server_defaults']['forward_secrecy'] = finding
                    
                    # Overall grade/rating from testssl.sh
                    elif finding_id in ['overall_grade', 'grade', 'rating', 'overall_rating']:
                        results['summary']['grade'] = finding
                    
    except Exception as e:
        print(f"Error parsing results: {str(e)}")
        # Fallback to basic parsing
        results['summary']['parse_error'] = str(e)
        results['summary']['raw_output'] = stdout[:2000]
    
    return results

def calculate_grade(results: dict) -> str:
    """Calculate security grade based on comprehensive results"""
    score = 100
    
    # Check protocols (major impact on score)
    protocols = results.get('protocols', {})
    if protocols.get('SSLv2', {}).get('supported'):
        score -= 40  # SSLv2 is critically insecure
    if protocols.get('SSLv3', {}).get('supported'):
        score -= 30  # SSLv3 is insecure (POODLE)
    if protocols.get('TLS1', {}).get('supported'):
        score -= 10  # TLS 1.0 is deprecated
    if protocols.get('TLS1_1', {}).get('supported'):
        score -= 10  # TLS 1.1 is deprecated
    if not protocols.get('TLS1_2', {}).get('supported'):
        score -= 20  # Should support TLS 1.2
    if not protocols.get('TLS1_3', {}).get('supported'):
        score -= 5   # Bonus for TLS 1.3
    
    # Check vulnerabilities
    vulnerabilities = results.get('vulnerabilities', {})
    for vuln_id, vuln_info in vulnerabilities.items():
        if vuln_info.get('vulnerable'):
            if vuln_info.get('severity') == 'CRITICAL':
                score -= 30
            elif vuln_info.get('severity') == 'HIGH':
                score -= 20
            elif vuln_info.get('severity') == 'MEDIUM':
                score -= 10
            else:
                score -= 5
    
    # Check ciphers
    ciphers = results.get('ciphers', {})
    weak_cipher_count = sum(1 for cipher_list in ciphers.values() 
                           for cipher in cipher_list 
                           if isinstance(cipher, dict) and cipher.get('strength') == 'weak')
    score -= weak_cipher_count * 5
    
    # Check certificate
    cert = results.get('certificate', {})
    if cert.get('cert_expired', '').lower() == 'true':
        score -= 50  # Expired certificate is critical
    
    # Check headers
    headers = results.get('headers', {})
    if not headers.get('HSTS'):
        score -= 5  # No HSTS
    
    # Calculate final grade
    if score >= 90:
        return 'A+'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    elif score >= 50:
        return 'D'
    else:
        return 'F'

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)