select 
    d_res.restaurant_id,
    d_res.cuisine,
    round(avg(d_res.rating), 2) as avg_restaurant_rating,
    d_res.rating_count as total_res_reviews,
    f_ord.order_date,
    sum(iff(f_ord.is_delivered, f_ord.sales_amount, 0)) as total_sales,
    f_ord.city,
    round(avg(f_ord.customer_rating), 2) as avg_order_rating,
    round(avg(f_ord.delivery_time_min), 2) as avg_delivery_time,
    count(*) as orders

from {{ ref('dim_restaurants') }} d_res

inner join {{ ref('fct_orders') }} f_ord
    on d_res.restaurant_id = f_ord.restaurant_id

group by 
    d_res.restaurant_id,
    d_res.cuisine,
    d_res.rating_count,
    f_ord.order_date,
    f_ord.city