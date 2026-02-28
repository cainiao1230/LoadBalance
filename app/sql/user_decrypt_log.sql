create table user_decrypt_log
(
    id           int auto_increment
        primary key,
    user_id      bigint   not null,
    decrypt_time datetime not null,
    constraint user_decrypt_log_ibfk_1
        foreign key (user_id) references sys_user (user_id)
);

create index user_id
    on user_decrypt_log (user_id);

INSERT INTO `decrypt-serve-admin`.user_decrypt_log (user_id, decrypt_time) VALUES (109, '2026-02-27 13:40:18');
