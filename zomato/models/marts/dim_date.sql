with spine as (
    select dateadd(day, seq4(), '2024-01-01'::date) as date
    from table(generator(rowcount => 1200))
)

select  
    date as order_date,
    year(date) as order_year,
    month(date) as order_month,
    monthname(date) as order_month_name,
    dayname(date) as order_day_name,
    (dayofweekiso(date) >= 6) as is_weekend,
from spine 
where order_date <= '2026-12-31'