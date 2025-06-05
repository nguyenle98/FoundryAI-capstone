-- This macro checks if a given column in a model contains only positive values.
{% test positive_value(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} <= 0
{% endtest %}