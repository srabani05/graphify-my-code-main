package com.example.web;

import com.example.model.Order;
import com.example.service.OrderService;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
    private final OrderService orders;
    private final JmsTemplate jms;

    public OrderController(OrderService orders, JmsTemplate jms) {
        this.orders = orders;
        this.jms = jms;
    }

    @PostMapping
    public Order create(@RequestBody Order order) {
        Order saved = orders.processOrder(order);
        jms.convertAndSend("order.events", saved.getId());
        return saved;
    }

    @GetMapping("/{id}")
    public Order get(@PathVariable String id) {
        return orders.processOrder(new Order(id));
    }
}
