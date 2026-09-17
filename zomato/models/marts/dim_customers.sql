select 
    customer_id,
    customer_name,
    email,
    case    when age < 18 then 'underage'
            when age < 25 then 'gen-z'
            when age < 40 then 'millennial'
            when age < 60 then 'gen-x'
            else 'baby-boomer' end as age,
    gender,
    marital_status,
    occupation,
    income_band,
    education
from {{ ref('stg_users') }}