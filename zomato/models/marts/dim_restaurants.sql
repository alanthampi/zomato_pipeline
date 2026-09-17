select
    restaurant_id,
    restaurant_name,
    city,
    cuisine,
    rating,
    rating_count,
    cost_for_two,
    license_no
from {{ ref('stg_restaurants') }} 