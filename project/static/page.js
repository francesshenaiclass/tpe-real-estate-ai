flowchart TD

subgraph group_g1["Data prep"]
  node_n1["Raw crawlers<br/>crawler/ingest<br/>[crawler.py]"]
  node_n2["JSON to CSV<br/>transform<br/>[json_to_csv.py]"]
  node_n3["Clean v1<br/>cleaning<br/>[clean_v1.py]"]
  node_n4["Merge pipeline<br/>[merge.py]"]
  node_n5["API merge<br/>etl<br/>[api_merge_all.py]"]
  node_n6["District cleaning<br/>[data_cleaning.py]"]
  node_n7["Geo enrich<br/>feature-engineering<br/>[mrt.py]"]
  node_n8["Real-price merge<br/>feature-build<br/>[process.py]"]
end

subgraph group_g2["Core app"]
  node_n9["Training entry<br/>[train_v3.py]"]
  node_n10[("Model artifacts<br/>[lgbm_real_mid.pkl]")]
  node_n11["API entry<br/>fastapi<br/>[main.py]"]
  node_n12["Predict API<br/>[predict_v3.py]"]
  node_n13["Recommend API<br/>[recommender.py]"]
  node_n14["Trends API<br/>analytics<br/>[market_trends.py]"]
  node_n15["Static maps<br/>reference-data<br/>[district_map.json]"]
  node_n16["HTML views<br/>ui<br/>[index.html]"]
end

subgraph group_g3["Legacy demos"]
  node_n17["Legacy API<br/>[api.py]"]
  node_n18["Quant dashboard<br/>[main.py]"]
  node_n19["Final price app<br/>[main.py]"]
end

node_n1 -->|"raw output"| node_n2
node_n2 -->|"clean"| node_n3
node_n3 -->|"merge"| node_n4
node_n1 -->|"district feeds"| node_n5
node_n6 -->|"enrich"| node_n7
node_n7 -->|"build table"| node_n8
node_n4 -->|"source data"| node_n8
node_n5 -->|"source data"| node_n8
node_n8 -->|"train on"| node_n9
node_n9 -->|"persist"| node_n10
node_n11 -->|"route"| node_n12
node_n11 -->|"route"| node_n13
node_n11 -->|"route"| node_n14
node_n11 -->|"load refs"| node_n15
node_n12 -->|"infer"| node_n10
node_n12 -->|"encode"| node_n15
node_n16 -->|"calls"| node_n11
node_n17 -->|"uses"| node_n15
node_n18 -->|"uses"| node_n15
node_n19 -->|"uses"| node_n15
node_n19 -.->|"infer"| node_n10

click node_n1 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/kevin/crawler.py"
click node_n2 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/kevin/json_to_csv.py"
click node_n3 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/kevin/clean_v1.py"
click node_n4 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/kevin/merge.py"
click node_n5 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/frances/api/api_merge_all.py"
click node_n6 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/永慶房屋/data_cleaning.py"
click node_n7 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/final/mrt.py"
click node_n8 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/實價登錄最終版/process.py"
click node_n9 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/train/train_v3.py"
click node_n10 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/train/models_v3_mrt_cluster/lgbm_real_mid.pkl"
click node_n11 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/main.py"
click node_n12 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/predict_v3.py"
click node_n13 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/recommender.py"
click node_n14 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/api/market_trends.py"
click node_n15 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/static/district_map.json"
click node_n16 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/project/templates/index.html"
click node_n17 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/taipeihouseapi/api.py"
click node_n18 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/taipei-real-estate-quant-engine/main.py"
click node_n19 "https://github.com/francesshenaiclass/tpe-real-estate-ai/blob/main/永慶房屋/main.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_n1,node_n2,node_n3,node_n4,node_n5,node_n6,node_n7,node_n8 toneBlue
class node_n9,node_n10,node_n11,node_n12,node_n13,node_n14,node_n15,node_n16 toneAmber
class node_n17,node_n18,node_n19 toneMint