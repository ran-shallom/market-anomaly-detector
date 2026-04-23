# Architecture Diagram

```mermaid
flowchart LR
    subgraph External["External Systems"]
        IB["IB Gateway (Windows)"]
        TG["Telegram API"]
        USER["User"]
    end

    subgraph Ingestion["Ingestion"]
        CONN["IBKR Connector\nsrc/input/ibkr/connector.py"]
    end

    subgraph Messaging["Messaging Layer"]
        KAFKA[("Kafka\nhist.* | live.* | anomalies")]
    end

    subgraph Processing["Realtime Processing"]
        DET["Anomaly Detector\nsrc/process/pipelines/live_detector.py"]
        REC["Bar Recorder\nsrc/input/streams/recorder.py"]
        ALERT["Alert Service\nsrc/output/alerts/service.py"]
        RETRAIN["Nightly Retrain\nsrc/process/pipelines/retrain.py"]
    end

    subgraph Storage["Storage"]
        DATA[("Parquet\nrealtime/data")]
        MODELS[("Model Artifacts\nrealtime/models")]
    end

    subgraph UI["Monitoring UI"]
        DASH["Streamlit Dashboard\nsrc/output/dashboard/app.py"]
    end

    IB -->|"historical + live bars"| CONN
    CONN -->|"publish hist.* / live.*"| KAFKA

    KAFKA -->|"consume hist.* / live.*"| DET
    KAFKA -->|"consume hist.* / live.*"| REC
    DET -->|"publish anomaly events"| KAFKA

    DET -->|"anomaly alert"| ALERT
    ALERT -->|"send message"| TG
    ALERT -->|"desktop notification"| USER

    REC -->|"append bars"| DATA
    DATA -->|"rolling 21-day window"| RETRAIN
    RETRAIN -->|"save updated weights + scaler"| MODELS
    MODELS -->|"load on startup + inference"| DET

    DATA -->|"latest bars"| DASH
    KAFKA -->|"anomalies topic"| DASH
    USER -->|"view dashboard"| DASH
```

## Notes

- `hist.*` topics seed model training at startup.
- `live.*` topics drive continuous detection.
- `anomalies` topic feeds dashboard event stream.
- Recorder and retrainer keep model behavior current with market drift.
