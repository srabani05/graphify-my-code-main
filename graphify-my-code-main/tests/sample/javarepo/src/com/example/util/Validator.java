package com.example.util;

import com.example.model.Order;

public class Validator {
    public static void check(Order order) {
        if (order == null) throw new IllegalArgumentException("null order");
    }
}
