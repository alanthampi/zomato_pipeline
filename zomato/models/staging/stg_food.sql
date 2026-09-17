select
item as food_name,
veg_or_non_veg
from {{ source('raw', 'FOOD') }} 