import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def train():
    data_path = os.getenv("RAW_DATA_PATH", "Data_engineering/Data_quality/raw_file/shipments 2.csv")
    ports_path = os.getenv("PORTS_DATA_PATH", "Data_engineering/Data_quality/raw_file/ports 2.csv")
    
    shipments = pd.read_csv(data_path)
    ports = pd.read_csv(ports_path)
    
    # Target definition: arrives > 24 hours after planned arrival[cite: 4]
    shipments['planned_arrival_dt'] = pd.to_datetime(shipments['planned_arrival'], errors='coerce')
    shipments['actual_arrival_dt'] = pd.to_datetime(shipments['actual_arrival'], errors='coerce')
    shipments['booking_date_dt'] = pd.to_datetime(shipments['booking_date'], errors='coerce')
    shipments['planned_departure_dt'] = pd.to_datetime(shipments['planned_departure'], errors='coerce')
    
    # Filter completed shipments
    df = shipments.dropna(subset=['actual_arrival_dt', 'planned_arrival_dt', 'planned_departure_dt', 'booking_date_dt']).copy()
    df = df[(df['weight_tons'] > 0) & (df['container_count'] > 0)]
    
    delay_hours = (df['actual_arrival_dt'] - df['planned_arrival_dt']).dt.total_seconds() / 3600.0
    df['target'] = (delay_hours > 24.0).astype(int)
    
    # Feature engineering strictly available at booking time[cite: 4]
    df['planned_transit_days'] = (df['planned_arrival_dt'] - df['planned_departure_dt']).dt.total_seconds() / 86400.0
    df['booking_lead_days'] = (df['planned_departure_dt'] - df['booking_date_dt']).dt.total_seconds() / 86400.0
    df['cargo_type'] = df['cargo_type'].fillna('UNKNOWN').astype(str).str.upper()
    
    ports_cong = ports.set_index('port_code')['avg_congestion_score'].to_dict()
    df['origin_congestion'] = df['origin_port'].map(ports_cong).fillna(0.5)
    df['dest_congestion'] = df['destination_port'].map(ports_cong).fillna(0.5)
    
    features = [
        'origin_port', 'destination_port', 'cargo_type',
        'weight_tons', 'container_count', 'planned_transit_days',
        'booking_lead_days', 'origin_congestion', 'dest_congestion'
    ]
    
    X = df[features]
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    cat_cols = ['origin_port', 'destination_port', 'cargo_type']
    num_cols = ['weight_tons', 'container_count', 'planned_transit_days', 'booking_lead_days', 'origin_congestion', 'dest_congestion']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)
        ]
    )
    
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    
    print("=== Model Evaluation Metrics ===")
    print(f"Precision: {precision_score(y_test, y_pred):.4f}")
    print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
    print(f"F1 Score:  {f1_score(y_test, y_pred):.4f}")
    print(f"ROC AUC:   {roc_auc_score(y_test, y_prob):.4f}")
    
    os.makedirs("ml_models", exist_ok=True)
    joblib.dump(pipeline, "ml_models/delay_model.joblib")
    print("Model artifact successfully saved to ml_models/delay_model.joblib")

if __name__ == "__main__":
    train()