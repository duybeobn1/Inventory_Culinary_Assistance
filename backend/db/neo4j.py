from neo4j import GraphDatabase
from config import get_settings
from logging_config import logger

settings = get_settings()

neo4j_driver = None

try:
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo4j_driver.verify_connectivity()
    logger.info("Neo4j connection established")
except Exception as e:
    logger.warning(f"Neo4j connection failed: {e}")
    neo4j_driver = None


def get_neo4j_session():
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver is not initialized")
    return neo4j_driver.session()


def close_neo4j():
    global neo4j_driver
    if neo4j_driver:
        neo4j_driver.close()
        logger.info("Neo4j driver closed")
        neo4j_driver = None
