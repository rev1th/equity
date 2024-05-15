
from dash import Dash, html, dash_table, dcc
from dash import callback, Output, Input
import pandas as pd

from main import get_table_data

app = Dash(__name__)

app.layout = html.Div([
    html.H3('HKEX Quant app'),
    html.Br(),
    html.Button('Load Analytics', id='load_main'),
    html.Div(id='curve-plot'),
])

@callback(
    Output(component_id='curve-plot', component_property='children'),
    Input(component_id='load_main', component_property='n_clicks'),
    # background=True,
    # running=[
    #     (Output("refresh", "disabled"), True, False),
    # ],
)
def load_main(*_):
    tabvals = []
    table = get_table_data()
    for k, v in table.items():
        v_df = pd.DataFrame(v).reset_index(names=['Name'])
        tabvals.append(dcc.Tab([
            dash_table.DataTable(
                data=v_df.to_dict('records'),
                columns=[{"name": vi, "id": vi} for vi in v_df.columns],
                sort_action='native',
                sort_mode='multi',
                sort_by=[],
            )
        ], label=k))
    return dcc.Tabs(children=tabvals)


if __name__ == '__main__':
    app.run(port=8051)
