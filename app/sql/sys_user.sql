create table sys_user
(
    user_id               bigint auto_increment comment '用户ID'
        primary key,
    user_name             varchar(30)                  not null comment '用户账号',
    phonenumber           varchar(11)  default ''      null comment '手机号码',
    sex                   char         default '0'     null comment '用户性别（0男 1女 2未知）',
    password              varchar(100) default ''      null comment '密码',
    status                char         default '0'     null comment '账号状态（0正常 1停用）',
    login_ip              varchar(128) default ''      null comment '最后登录IP',
    login_date            datetime                     null comment '最后登录时间',
    pwd_update_date       datetime                     null comment '密码最后更新时间',
    priority              int          default 1       null comment '优先级（数字越小优先级越高）',
    remaining_requests    int          default 0       null comment '剩余请求次数（-1表示无限制）',
    total_requests        int          default -1      null comment '总请求次数（最初分配的请求次数，-1表示无限制）',
    create_by             varchar(64)  default 'admin' null comment '创建者',
    create_time           datetime                     null comment '创建时间',
    update_by             varchar(64)  default 'admin' null comment '更新者',
    update_time           datetime                     null comment '这个字段只会在更新优先级和创建优先级的情况下改变',
    remark                varchar(500)                 null comment '备注',
    lastRequestTime       datetime                     null comment '最后一次请求时间（从队列中拿出来的时间，发往服务器之前的时间）',
    totalUpdateTime       datetime                     null comment '总数更新时间',
    decrypt_success_count int          default 0       null comment '用来记录该用户解出密钥成功的数量'
)
    comment '用户信息表';

INSERT INTO `decrypt-serve-admin`.sys_user (user_name, phonenumber, sex, password, status, login_ip, login_date, pwd_update_date, priority, remaining_requests, total_requests, create_by, create_time, update_by, update_time, remark, lastRequestTime, totalUpdateTime, decrypt_success_count) VALUES ('ceshi', '', '0', 'u6R3c8gCWB/eByV5k2+PjA==', '0', '', null, null, 1, 200, -1, 'admin', null, 'admin', null, null, null, null, 0);
INSERT INTO `decrypt-serve-admin`.sys_user (user_name, phonenumber, sex, password, status, login_ip, login_date, pwd_update_date, priority, remaining_requests, total_requests, create_by, create_time, update_by, update_time, remark, lastRequestTime, totalUpdateTime, decrypt_success_count) VALUES ('测试', '', '0', 'u6R3c8gCWB/eByV5k2+PjA==', '0', '', null, null, 5, 2039, 3000, 'wtxlj', '2026-02-03 10:26:49', 'wtxlj', '2026-02-03 10:26:49', null, '2026-02-27 13:40:18', null, 4);
INSERT INTO `decrypt-serve-admin`.sys_user (user_name, phonenumber, sex, password, status, login_ip, login_date, pwd_update_date, priority, remaining_requests, total_requests, create_by, create_time, update_by, update_time, remark, lastRequestTime, totalUpdateTime, decrypt_success_count) VALUES ('ceshi1', '', '0', 'txjfRFmZiTKBXHQSt9g1NA==', '0', '', null, null, 2, 150, -1, 'admin', null, 'wtxlj', '2026-02-09 14:28:15', null, null, '2026-02-09 14:27:59', 0);
