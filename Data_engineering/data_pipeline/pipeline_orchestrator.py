import configparser
import sys
import os
import logging
from bronze_loader import load_bronze
from silver_transformer import transform_silver
from gold_aggregator import build_gold

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
PIPELINE_LOG_FILE = os.path.join(LOG_DIR, "data_pipeline.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [DataPipeline]: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PIPELINE_LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger("DataPipeline")

def run_pipeline():
    config = configparser.ConfigParser()
    config.read("settings.config")

    logger.info("=== Starting Data Pipeline Run ===")
    try:
        logger.info("[Step 1/3]: Starting Bronze Loader (Staging Truncate & Load)")
        load_bronze(config)
        logger.info("[Step 1/3]: Bronze Loader finished successfully.")

        logger.info("[Step 2/3]: Starting Silver Transformer (SCD Type 2 & Business Metrics)")
        transform_silver(config)
        logger.info("[Step 2/3]: Silver Transformer finished successfully.")

        logger.info("[Step 3/3]: Starting Gold Aggregator (Star Schema / Fact & Dim Tables)")
        build_gold(config)
        logger.info("[Step 3/3]: Gold Aggregator finished successfully.")

        logger.info("=== Pipeline Execution Completed Successfully ===")
    except Exception as e:
        logger.exception(f"Pipeline execution aborted due to error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()