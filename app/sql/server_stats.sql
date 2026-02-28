create table server_stats
(
    id            int auto_increment
        primary key,
    ip            varchar(64)   not null,
    username      varchar(64)   not null,
    password      varchar(128)  not null,
    keygen_busy   int default 0 null,
    key_success   int default 0 null,
    request_total int default 0 null
);

