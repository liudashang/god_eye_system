CREATE TABLE fping_metrics
(
    host        String COMMENT '目标主机IP/域名',
    loss_now    Float32 COMMENT '当前丢包率(0~100)',
    med_now     Float32 COMMENT '中位延迟 ms',
    node_path   String COMMENT '节点路径/归属标识',
    `timestamp` DateTime COMMENT '采集时间戳'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(`timestamp`)
ORDER BY (host, `timestamp`)
PRIMARY KEY (host, `timestamp`)
TTL `timestamp` + INTERVAL 30 DAY DELETE
SETTINGS index_granularity = 8192;