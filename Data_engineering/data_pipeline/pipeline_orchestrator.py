import configparser
import sys
from bronze_loader import load_bronze
from silver_transformer import transform_silver
from gold_aggregator import build_gold

def run_pipeline():
    config = configparser.ConfigParser()
    config.read("settings.config")

    print("--- Starting Pipeline Run ---")
    try:
        print("\n[Step 1/3]: Bronze Loader")
        load_bronze(config)

        print("\n[Step 2/3]: Silver Transformer (SCD2)")
        transform_silver(config)

        print("\n[Step 3/3]: Gold Aggregator (Star Schema)")
        build_gold(config)

        print("\n--- Pipeline Run Completed Successfully ---")
    except Exception as e:
        print(f"\nPipeline execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()