select 
    city,
    order_date,
    count(*) as total_orders,
    sum(iff(is_delivered, sales_amount, 0)) as total_revenue,
    count_if(is_delivered) as total_delivered,
    round(div0(count_if(order_status = 'cancelled'), count(*)), 2) as cancellation_rate,
    round(div0(sum(iff(is_delivered, sales_amount, 0)), count_if(is_delivered)), 2) as avg_order_value
    from {{ ref('fct_orders') }} 
    group by 1,2
