import io
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import dash
import time
import webbrowser
from threading import Timer
import socket

# --- Build the Dash App ---
app = Dash(__name__)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Styles for the initial full-page spinner */
            #initial-loading {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: white;
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 1;
                transition: opacity 0.5s;  /* Add smooth transition */
            }
            /* A simple CSS spinner */
            .spinner {
                border: 16px solid #f3f3f3; /* Light gray */
                border-top: 16px solid #3498db; /* Blue */
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 2s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <!-- Initial loading spinner -->
        <div id="initial-loading">
            <div class="spinner"></div>
        </div>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            <script>
                // Add a minimum delay before hiding the spinner
                window.addEventListener('load', function() {
                    setTimeout(function() {
                        var loader = document.getElementById('initial-loading');
                        if (loader) {
                            loader.style.opacity = '0';
                            setTimeout(function() {
                                loader.style.display = 'none';
                            }, 500);
                        }
                    }, 1000); // 1 second minimum display time
                });
            </script>
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Updated layout using the structure from visualize_tricks_rough.py
app.layout = html.Div([
    # 1. Header Section
    html.Div([
        html.H1("Skateboarding Flatground Flip Tricks Visualization", style={"textAlign": "center", "margin": "0"}),
    ], style={"padding": "10px", "backgroundColor": "#f9f9f9"}),

    # 2. Control Panel
    html.Div([
        html.Div([
            html.Label("View Mode: "),
            dcc.RadioItems(
                id='view-toggle',
                options=[
                    {'label': '3D View', 'value': '3D'},
                    {'label': '2D View', 'value': '2D'}
                ],
                value='3D',
                labelStyle={'display': 'inline-block', 'marginRight': '10px'}
            )
        ], style={"flex": "1", "minWidth": "250px", "margin": "10px"}),

        html.Div([
            html.Button("Reset", id='reset-button', n_clicks=0, style={'height': '40px'})
        ], style={"flex": "1", "minWidth": "150px", "margin": "10px", "alignSelf": "center"})
    ], style={
        "display": "flex",
        "flexWrap": "wrap",
        "justifyContent": "center",
        "alignItems": "center",
        "backgroundColor": "#f9f9f9"
    }),

    # Hidden stores: one for camera and one for the selected trick.
    dcc.Store(id="camera-store"),
    dcc.Store(id="selected-trick"),

    # 3. Main Content: Graph and Trick Info Panel
    html.Div([
        # Graph Container fills available space
        html.Div([
            dcc.Graph(
                id='trick-graph',
                style={
                    "height": "calc(100vh - 250px)",  # Subtract approximate height of header + controls
                    "width": "100%"
                }
            )
        ], style={
            "flex": "3",  # Takes up 75% of the space
            "minWidth": "0"
        }),
        # Trick Info Panel
        html.Div(id='trick-info', style={
            'padding': '10px',
            'border': '1px solid #ccc',
            'marginLeft': '10px',
            'flex': '0.25',  # Takes up 25% of the space
            'minWidth': '200px',
            'overflowY': 'auto'  # Allows scrolling if content is too long
        })
    ], style={
        "display": "flex",
        "flexDirection": "row",
        "flex": "1",
        "width": "100%",
        "padding": "10px",
        "gap": "10px"
    })
], style={
    "display": "flex",
    "flexDirection": "column",
    "height": "100vh",
    "width": "100%",
    "margin": "0",
    "padding": "0",
    "overflow": "hidden"
})

# --- Clientside callback to update the camera-store from relayoutData ---
app.clientside_callback(
    """
    function(relayoutData, storedCamera) {
        if (relayoutData && relayoutData["scene.camera"]) {
            return relayoutData["scene.camera"];
        }
        return storedCamera || window.dash_clientside.no_update;
    }
    """,
    Output("camera-store", "data"),
    Input("trick-graph", "relayoutData"),
    State("camera-store", "data")
)

# --- Callback to update the selected trick (via a hidden store) based on click events ---
@app.callback(
    Output('selected-trick', 'data'),
    [Input('trick-graph', 'clickData'),
     Input('reset-button', 'n_clicks')],
    State('view-toggle', 'value')
)
def update_selected_trick(clickData, n_clicks, view):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    trigger_id = ctx.triggered[0]['prop_id']
    # If the reset button is clicked, clear the selection.
    if 'reset-button' in trigger_id:
        return None
    if clickData is None:
        return dash.no_update
    point_data = clickData['points'][0]
    point_idx = point_data.get('pointIndex', point_data.get('pointNumber'))
    global df_2d, df_3d
    df_used = df_3d if view == "3D" else df_2d
    if point_idx is not None and point_idx < len(df_used):
        trick_name = df_used.iloc[point_idx]["Trick Name"]
        return trick_name
    return dash.no_update

# --- Callback to update the graph and info panel, preserving camera and handling trick selection ---
@app.callback(
    [Output('trick-graph', 'figure'),
     Output('trick-info', 'children')],
    [Input('view-toggle', 'value'),
     Input('camera-store', 'data'),
     Input('selected-trick', 'data')]
)
def update_graph(view, stored_camera, selected_trick):
    use_3d = view == '3D'
    global df_2d, df_3d
    data_df = df_3d if use_3d else df_2d

    # Helper: determine default marker color based on the trick.
    def default_color(row):
        if pd.isna(row['Trick Name']) or row['Trick Name'].strip() == "":
            return 'lightgray'
        elif row['Has_Asterisk']:
            return 'purple'
        else:
            return 'blue'

    colors = []
    sizes = []
    text_colors = []

    # If a trick is selected (stored via the hidden store), find it.
    if selected_trick:
        selected_rows = data_df[data_df["Trick Name"] == selected_trick]
        if not selected_rows.empty:
            clicked_trick = selected_rows.iloc[0]
            selected_spin = clicked_trick["Spin Rotation"]
            selected_flip = clicked_trick["Flip Rotation"]
            selected_body = clicked_trick["Body Rotation"] if use_3d else None
        else:
            clicked_trick = None
    else:
        clicked_trick = None

    # Build marker styles.
    for idx, row in data_df.iterrows():
        if clicked_trick is not None:
            # Highlight any trick that shares a rotation (only if nonzero).
            if ((row["Spin Rotation"] == selected_spin and row["Spin Rotation"] != 0) or 
                (row["Flip Rotation"] == selected_flip and row["Flip Rotation"] != 0) or
                (use_3d and row["Body Rotation"] == selected_body and row["Body Rotation"] != 0)):
                colors.append('red')
                sizes.append(24)
                text_colors.append('black')
            else:
                colors.append('lightgray')
                sizes.append(8)
                text_colors.append('rgba(0,0,0,0)')
        else:
            colors.append(default_color(row))
            sizes.append(20 if row["Trick Name"].strip() else 8)
            text_colors.append('black')

    # Build the main scatter trace.
    if use_3d:
        scatter = go.Scatter3d(
            x = data_df['Spin Rotation'],
            y = data_df['Flip Rotation'],
            z = data_df['Body Rotation'],
            mode = 'markers+text',
            marker = dict(size=sizes, color=colors, opacity=0.6),
            text = data_df['Trick Name'],
            textposition = 'top center',
            textfont = dict(size=8, color=text_colors),
            hovertemplate = (
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<br>' +
                'Body Rotation: %{z}<extra></extra>'
            ),
            name = 'Confirmed Tricks',
            legendgroup='tricks',
            showlegend = (clicked_trick is None)
        )
    else:
        scatter = go.Scatter(
            x = data_df['Spin Rotation'],
            y = data_df['Flip Rotation'],
            mode = 'markers+text',
            marker = dict(size=sizes, color=colors, opacity=0.6),
            text = data_df['Trick Name'],
            textposition = 'top center',
            textfont = dict(size=8, color=text_colors),
            hovertemplate = (
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<extra></extra>'
            ),
            name = 'Confirmed Tricks',
            legendgroup='tricks',
            showlegend = (clicked_trick is None)
        )
       
    fig = go.Figure(data=[scatter])
    
    # Dummy trace for the "Unconfirmed Tricks" legend item.
    if use_3d:
        dummy = go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode='markers',
            marker=dict(size=20, color='purple', opacity=0.6),
            name='Unconfirmed Tricks',
            showlegend = (clicked_trick is None)
        )
    else:
        dummy = go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=20, color='purple', opacity=0.6),
            name='Unconfirmed Tricks',
            showlegend = (clicked_trick is None)
        )
    fig.add_trace(dummy)
    
    # If a trick is selected, add connection lines and build the info panel.
    if clicked_trick is not None:
        spin_line_x, spin_line_y, spin_line_z = [], [], []
        flip_line_x, flip_line_y, flip_line_z = [], [], []
        if use_3d:
            body_line_x, body_line_y, body_line_z = [], [], []
        for idx, row in data_df.iterrows():
            if row["Trick Name"] == clicked_trick["Trick Name"]:
                continue
            if row["Spin Rotation"] == selected_spin and row["Spin Rotation"] != 0:
                spin_line_x += [selected_spin, row["Spin Rotation"], None]
                spin_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                if use_3d:
                    spin_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]
            if row["Flip Rotation"] == selected_flip and row["Flip Rotation"] != 0:
                flip_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                flip_line_y += [selected_flip, row["Flip Rotation"], None]
                if use_3d:
                    flip_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]
            if use_3d and row["Body Rotation"] == selected_body and row["Body Rotation"] != 0:
                body_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                body_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                body_line_z += [selected_body, row["Body Rotation"], None]
        if spin_line_x:
            if use_3d:
                fig.add_trace(go.Scatter3d(
                    x=spin_line_x,
                    y=spin_line_y,
                    z=spin_line_z,
                    mode='lines',
                    line=dict(color='green', width=3),
                    name='Spin Connection',
                    hoverinfo='skip'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=spin_line_x,
                    y=spin_line_y,
                    mode='lines',
                    line=dict(color='green', width=3),
                    name='Spin Connection',
                    hoverinfo='skip'
                ))
        if flip_line_x:
            if use_3d:
                fig.add_trace(go.Scatter3d(
                    x=flip_line_x,
                    y=flip_line_y,
                    z=flip_line_z,
                    mode='lines',
                    line=dict(color='magenta', width=3),
                    name='Flip Connection',
                    hoverinfo='skip'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=flip_line_x,
                    y=flip_line_y,
                    mode='lines',
                    line=dict(color='magenta', width=3),
                    name='Flip Connection',
                    hoverinfo='skip'
                ))
        if use_3d and body_line_x:
            fig.add_trace(go.Scatter3d(
                x=body_line_x,
                y=body_line_y,
                z=body_line_z,
                mode='lines',
                line=dict(color='orange', width=3),
                name='Body Connection',
                hoverinfo='skip'
            ))
        # Build the info panel.
        spin_direction = ""
        if clicked_trick["Spin Rotation"] < 0:
            spin_direction = "Backside"
        elif clicked_trick["Spin Rotation"] > 0:
            spin_direction = "Frontside"
        info_items = [
            html.H4(clicked_trick["Trick Name"]),
            html.P(f"Spin Rotation: {clicked_trick['Spin Rotation']}"),
            html.P(f"Flip Rotation: {clicked_trick['Flip Rotation']}")
        ]
        if use_3d:
            info_items.append(html.P(f"Body Rotation: {clicked_trick['Body Rotation']}"))
        if spin_direction:
            info_items.append(html.P(f"Direction: {spin_direction}"))
        info_content = html.Div(info_items)
    else:
        info_content = html.Div("Click on a trick to get more information.", style={'fontStyle': 'italic'})
       
    # Layout configuration.
    if use_3d:
        layout_settings = dict(
            margin=dict(l=0, r=0, b=0, t=0),
            scene=dict(
                xaxis=dict(title='Spin Rotation', tickmode='linear', dtick=180),
                yaxis=dict(title='Flip Rotation', tickmode='linear', dtick=360),
                zaxis=dict(title='Body Rotation', tickmode='linear', dtick=180),
                camera=stored_camera if stored_camera else {}
            ),
            showlegend=True,
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right',
                y=0.98,
                yanchor='top'
            )
        )
    else:
        layout_settings = dict(
            margin=dict(l=50, r=50, b=50, t=50),
            xaxis=dict(title='Spin Rotation', tickmode='linear', dtick=180),
            yaxis=dict(title='Flip Rotation', tickmode='linear', dtick=360),
            showlegend=True,
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right',
                y=0.98,
                yanchor='top'
            )
        )
    fig.update_layout(**layout_settings)
    return fig, info_content

if __name__ == '__main__':
    # Load and cache dataframes.
    df = pd.read_csv("trick_names.csv", comment='#', skip_blank_lines=True)
    df['Trick Name'] = df['Trick Name'].str.strip()
    
    # Add a column to track if the trick had an asterisk.
    df['Has_Asterisk'] = df['Trick Name'].str.contains(r'\*')
    
    # Remove text within parentheses and asterisks, then strip whitespace.
    df['Trick Name'] = df['Trick Name'].str.replace(r'\s*\([^)]*\)', '', regex=True)
    df['Trick Name'] = df['Trick Name'].str.replace(r'\*', '', regex=True).str.strip()
    
    # Cache 2D and 3D dataframes.
    df_2d = df[df["Body Rotation"] == 0].copy()
    df_3d = df.copy()
    
    def wait_for_server(port, timeout=5):
        start_time = time.time()
        while True:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.1)
                webbrowser.open(f'http://127.0.0.1:{port}')
                break
            except (socket.error, socket.timeout):
                if time.time() - start_time > timeout:
                    break
                time.sleep(0.1)

    port = 8050
    Timer(0.1, lambda: wait_for_server(port)).start()
    app.run_server(debug=False, port=port)
