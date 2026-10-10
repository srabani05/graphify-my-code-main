package com.example.mapper;

import com.example.model.Order;
import org.apache.ibatis.annotations.Select;

public interface OrderMapper {
    @Select("SELECT id, paid FROM orders WHERE id = #{id}")
    Order getById(String id);
}
