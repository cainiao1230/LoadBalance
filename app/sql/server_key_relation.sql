create table server_key_relation
(
    id           int auto_increment comment '主键'
        primary key,
    server_id    int      not null comment '服务器编号',
    decrypt_time datetime not null comment '解密成功时间',
    user_id      int      not null comment '用户ID'
)
    comment '服务器与密钥关系表';

