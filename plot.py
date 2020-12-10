from sqlalchemy import create_engine
import altair as alt
import pandas as pd

engine = create_engine('sqlite:///file:site-checker.db?mode=ro&uri=true')

sql = """
with max_check_date as (
SELECT
max(checked_date) as checked_date
from
status
)

SELECT
datetime(s.checked_date, 'unixepoch', 'localtime') as timestamp,
s.site_name,
s.status_code,
CASE
    when s.elapsed is NULL THEN -1
    ELSE s.elapsed
END as elapsed,
s.success

FROM
status as s,
max_check_date as m

WHERE
s.site_name = 'classic_catalog'
AND s.checked_date >= (m.checked_date - (3600 * 2))
order by s.checked_date DESC
"""

df = pd.read_sql(sql=sql, con=engine)

df.to_csv('current.csv')

alt.Chart(df).mark_line(clip=True).encode(
    x=alt.X('timestamp:T',
            axis=alt.Axis(labelAngle=-45)
           
           ),
    y=alt.Y('elapsed:Q',
            scale=alt.Scale(domain=(-1, 5)),
            axis=alt.Axis(title='elapsed time of request (seconds)'),
           )
#     y='elapsed:Q',
#     tooltip=['month_created:T', 'count']
).properties(
    title='Last 2-Hours HTTP Respose Times (-1 Indicates Timeout Occurred)',
    width=1100
).save('current.html')