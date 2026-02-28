
from app.packet_parser import get_drone_id, demask_for_176_byte, hex_string_to_bytes

if __name__ == "__main__":

    test_data="98,82,9b,5c,f3,32,1a,be,9b,ff,79,ca,4a,9e,2d,8a,6d,4e,80,e4,56,83,45,45,28,ab,27,65,0f,f7,e9,a6,88,2d,38,c0,c7,86,34,ab,d6,05,37,f1,bc,9c,5b,46,b9,ec,d9,ae,4d,8a,8e,dd,60,d4,cd,97,f8,3d,ca,99,dc,a8,29,ef,21,6a,c1,1e,d6,0e,5e,b8,db,71,9f,7c,cb,99,85,33,2c,fa,ba,27,4d,e8,2e,43,f8,ab,f2,a9,cb,fd,86,ea,62,54,ca,43,6e,62,83,19,87,9d,59,61,86,f6,d0,95,f1,22,09,78,77,e7,df,04,c4,0b,57,c9,70,31,39,78,15,a6,b4,e3,42,44,9b,d4,3b,f7,b7,d4,a2,9e,7b,81,fb,dd,4b,4d,06,b1,77,5a,4c,4d,fa,67,5d,d1,54,55,8b,a0,39,85,eb,03,15,74,0b,26,af,12"
    test_key="8d,b7,9b,da,f0,c1,2f,8d,8d,b5,52,59,ad,c7,1d,1b,0d,74,61,41,fa,1a,f8,5a,be,26,d0,32,e7,14,d8,1d,39,97,80,59,e6,cb,15,57,e6,a1,bf,ee,11,20,a1,06,0e,d9,8e,f2,f9,11,eb,38,3a,c1,15,64,d5,5b,38,d8,7a,6d,66,f5,b7,0c,fe,c1,6e,ab,5e,9d,e9,45,07,7c,06,07,f6,01,db,93,e0,27,6d,e8,f9,6b,c4,07,2b,7a,cf,38,f9,39,8a,34,c0,b4,6e,62,aa,bE,87,03,1f,5f,9a,a4,8f,35,f1,40,74,ae,b1,a8,60,a5,17,dc,ad,c9,70,57,ac,e6,93,3d,40,"
    test_data=hex_string_to_bytes(test_data)
    print(get_drone_id(demask_for_176_byte(test_data)))
    #测试同一架飞机的密钥包和数据包无人机id是否相同