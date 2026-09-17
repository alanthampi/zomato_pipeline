select 
    menu_id,
    try_to_number(r_id) as restaurant_id,
    f_id as food_id,
    cuisine,
    try_to_decimal(nullif(price, ' -- '), 10, 2) as price
from {{ source('raw', 'MENU')}}
where restaurant_id is not null and price is not null