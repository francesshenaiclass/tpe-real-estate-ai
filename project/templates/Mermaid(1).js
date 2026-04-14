flowchart TD

subgraph group_serving["Serving app"]
  node_project_main["Main app<br/>FastAPI entry<br/>[main.py]"]
  node_predict_v3["Predictor<br/>range inference<br/>[predict_v3.py]"]
  node_recommender["Recommender<br/>ranking logic<br/>[recommender.py]"]
  node_market_trends["Trends API<br/>analytics API<br/>[market_trends.py]"]
  node_models_runtime[("Model files<br/>LightGBM artifacts")]
  node_static_geo["Geo lookup<br/>reference data"]
  node_templates["UI templates<br/>presentation"]
end

subgraph group_training["Training"]
  node_train_v3["Train v3<br/>model training<br/>[train_v3.py]"]
  node_train_artifacts[("Train outputs<br/>trained models")]
  node_train_all["Alt trainer<br/>training pipeline<br/>[train_all.py]"]
end

subgraph group_etl["ETL and data prep"]
  node_final_etl["Final merge<br/>dataset fusion"]
  node_yongqing["Yongqing ETL<br/>crawler-cleaner"]
  node_real_reg_etl["Registry ETL<br/>official-data pipeline"]
  node_frances_etl["Frances ETL<br/>aggregation pipeline"]
  node_kevin_etl["Kevin ETL<br/>crawler-cleaner"]
end

subgraph group_legacy["Legacy branches"]
  node_kevin_api2["Kevin API<br/>legacy UI<br/>[api2.py]"]
  node_quant_engine["Quant engine<br/>prototype app<br/>[main.py]"]
  node_house_api["House API<br/>legacy dashboard<br/>[api.py]"]
end

node_project_main -->|"routes prediction"| node_predict_v3
node_project_main -->|"routes recommendation"| node_recommender
node_project_main -->|"routes trends"| node_market_trends
node_project_main -->|"renders UI"| node_templates
node_predict_v3 -->|"loads models"| node_models_runtime
node_predict_v3 -->|"uses lookups"| node_static_geo
node_recommender -->|"shares features"| node_static_geo
node_market_trends -->|"aggregates geography"| node_static_geo
node_train_v3 -->|"consumes data"| node_final_etl
node_train_v3 -->|"writes artifacts"| node_train_artifacts
node_train_artifacts -->|"deploys models"| node_models_runtime
node_final_etl -->|"merges sources"| node_real_reg_etl
node_final_etl -->|"joins context"| node_yongqing
node_final_etl -->|"absorbs outputs"| node_frances_etl
node_final_etl -->|"absorbs outputs"| node_kevin_etl
node_train_all -.->|"alternate path"| node_train_artifacts
node_kevin_api2 -.->|"legacy branch"| node_kevin_etl
node_quant_engine -.->|"prototype branch"| node_real_reg_etl
node_house_api -.->|"legacy branch"| node_final_etl

click node_project_main "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/main.py"
click node_predict_v3 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/predict_v3.py"
click node_recommender "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/recommender.py"
click node_market_trends "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/market_trends.py"
click node_models_runtime "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/project/models"
click node_static_geo "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/project/static"
click node_templates "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/project/templates"
click node_train_v3 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/train/train_v3.py"
click node_train_artifacts "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/train/models_v3_mrt_cluster"
click node_train_all "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/train/train_all.py"
click node_final_etl "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/final"
click node_yongqing "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/永慶房屋"
click node_real_reg_etl "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/實價登錄最終版"
click node_frances_etl "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/frances"
click node_kevin_etl "https://github.com/francesshenaiclass/tpe-real-estate-ai/tree/main/kevin"
click node_kevin_api2 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/kevin/api2/api2.py"
click node_quant_engine "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/taipei-real-estate-quant-engine/main.py"
click node_house_api "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/taipeihouseapi/api.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_project_main,node_predict_v3,node_recommender,node_market_trends,node_models_runtime,node_static_geo,node_templates toneBlue
class node_train_v3,node_train_artifacts,node_train_all toneAmber
class node_final_etl,node_yongqing,node_real_reg_etl,node_frances_etl,node_kevin_etl toneMint
class node_kevin_api2,node_quant_engine,node_house_api toneRose