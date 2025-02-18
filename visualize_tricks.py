import io
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import dash

# Read CSV while ignoring commented lines.
df = pd.read_csv("trick_names.csv", comment='#', skip_blank_lines=True)
df['Trick Name'] = df['Trick Name'].str.strip()

# --- Build the Dash App ---
app = Dash(__name__)

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
                labelStyle={'display': 'inline-block', 'margin-right': '10px'}
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

    # Hidden store to keep track of the latest camera settings
    dcc.Store(id="camera-store"),

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
        # Trick Info Panel - now horizontal
        html.Div(id='trick-info', style={
            'padding': '10px',
            'border': '1px solid #ccc',
            'margin-left': '10px',
            'flex': '0.25',  # Takes up 25% of the space
            'minWidth': '200px',
            'overflowY': 'auto'  # Allows scrolling if content is too long
        })
    ], style={
        "display": "flex",
        "flexDirection": "row",  # Changed to row to place items horizontally
        "flex": "1",
        "width": "100%",
        "padding": "10px",
        "gap": "10px"  # Adds space between graph and info panel
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
        // Otherwise, keep the stored value (or no update if not set yet)
        return storedCamera || window.dash_clientside.no_update;
    }
    """,
    Output("camera-store", "data"),
    Input("trick-graph", "relayoutData"),
    State("camera-store", "data")
)

# --- Callback to reset the graph selection ---
@app.callback(
    Output('trick-graph', 'clickData'),
    Input('reset-button', 'n_clicks')
)
def reset_selection(n_clicks):
    if n_clicks > 0:
        return None
    return dash.no_update

# --- Callback to update the graph and info panel, preserving camera ---
@app.callback(
    [Output('trick-graph', 'figure'),
     Output('trick-info', 'children')],
    [Input('view-toggle', 'value'),
     Input('trick-graph', 'clickData')],
    [State('camera-store', 'data')]
)
def update_graph(view, clickData, stored_camera):
    # For 3D view, use full dataframe.
    # For 2D view, filter out tricks that have body rotation not equal to zero.
    use_3d = view == '3D'
    if use_3d:
        data_df = df
    else:
        data_df = df[df["Body Rotation"] == 0]

    # Create the scatter plot using the filtered data.
    if use_3d:
        scatter = go.Scatter3d(
            x=data_df['Spin Rotation'],
            y=data_df['Flip Rotation'],
            z=data_df['Body Rotation'],
            mode='markers+text',
            marker=dict(size=12, color='blue', opacity=0.8),
            text=data_df['Trick Name'],
            textposition='top center',
            textfont=dict(size=8, color='black'),
            customdata=data_df[['Spin Rotation', 'Flip Rotation', 'Body Rotation', 'Trick Name']].values,
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<br>' +
                'Body Rotation: %{z}<extra></extra>'
            ),
            name='Tricks'
        )
        fig = go.Figure(data=[scatter])
        scene_layout = dict(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            zaxis_title='Body Rotation',
            xaxis=dict(tickmode='array', tickvals=[-1080, -900, -720, -540, -360, -180, 0, 180, 360, 540, 720, 900, 1080], 
                      ticktext=['-1080°', '-900°', '-720°', '-540°', '-360°', '-180°', '0°', '180°', '360°', '540°', '720°', '900°', '1080°']),
            yaxis=dict(tickmode='array', tickvals=[-1080, -900, -720, -540, -360, -180, 0, 180, 360, 540, 720, 900, 1080],
                      ticktext=['-1080°', '-900°', '-720°', '-540°', '-360°', '-180°', '0°', '180°', '360°', '540°', '720°', '900°', '1080°']),
            zaxis=dict(tickmode='array', tickvals=[-1080, -900, -720, -540, -360, -180, 0, 180, 360, 540, 720, 900, 1080],
                      ticktext=['-1080°', '-900°', '-720°', '-540°', '-360°', '-180°', '0°', '180°', '360°', '540°', '720°', '900°', '1080°'])
        )
        if stored_camera:
            scene_layout["camera"] = stored_camera
        fig.update_layout(
            scene=scene_layout,
            margin=dict(l=0, r=0, b=0, t=0),
            uirevision="constant",
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right'
            )
        )
    else:
        scatter = go.Scatter(
            x=data_df['Spin Rotation'],
            y=data_df['Flip Rotation'],
            mode='markers+text',
            marker=dict(size=12, color='blue', opacity=0.8),
            text=data_df['Trick Name'],
            textposition='top center',
            textfont=dict(size=8, color='black'),
            customdata=data_df[['Spin Rotation', 'Flip Rotation', 'Trick Name']].values,
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<extra></extra>'
            ),
            name='Tricks'
        )
        fig = go.Figure(data=[scatter])
        fig.update_layout(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            xaxis=dict(tickmode='array', tickvals=[-1080, -900, -720, -540, -360, -180, 0, 180, 360, 540, 720, 900, 1080],
                      ticktext=['-1080°', '-900°', '-720°', '-540°', '-360°', '-180°', '0°', '180°', '360°', '540°', '720°', '900°', '1080°']),
            yaxis=dict(tickmode='array', tickvals=[-1080, -900, -720, -540, -360, -180, 0, 180, 360, 540, 720, 900, 1080],
                      ticktext=['-1080°', '-900°', '-720°', '-540°', '-360°', '-180°', '0°', '180°', '360°', '540°', '720°', '900°', '1080°']),
            margin=dict(l=0, r=0, b=0, t=0),
            uirevision="constant",
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right'
            )
        )

    # Default info message.
    info_content = html.Div("Click on a trick to get more information.", style={'font-style': 'italic'})

    if clickData is not None:
        point_data = clickData['points'][0]
        point_idx = point_data.get('pointIndex', point_data.get('pointNumber'))
        # If the index is no longer valid (e.g., clicked trick has nonzero body rotation and isn't in data_df), ignore clickData.
        if point_idx is None or point_idx >= len(data_df):
            return fig, info_content

        clicked_trick = data_df.iloc[point_idx]
        selected_spin = clicked_trick["Spin Rotation"]
        selected_flip = clicked_trick["Flip Rotation"]

        # Build the info panel.
        info_items = [
            html.H4(clicked_trick["Trick Name"]),
            html.P(f"Spin Rotation: {clicked_trick['Spin Rotation']}"),
            html.P(f"Flip Rotation: {clicked_trick['Flip Rotation']}")
        ]
        if use_3d:
            info_items.append(html.P(f"Body Rotation: {clicked_trick['Body Rotation']}"))
        info_content = html.Div(info_items)

        # Build connection lines and update marker styling.
        colors = []
        sizes = []
        spin_line_x, spin_line_y, spin_line_z = [], [], []
        flip_line_x, flip_line_y, flip_line_z = [], [], []
        if use_3d:
            body_line_x, body_line_y, body_line_z = [], [], []
        else:
            body_line_x = body_line_y = body_line_z = None

        for idx, row in data_df.iterrows():
            # A trick is highlighted if ANY of its rotations match
            if (row["Spin Rotation"] == selected_spin or 
                row["Flip Rotation"] == selected_flip or 
                (use_3d and row["Body Rotation"] == clicked_trick["Body Rotation"])):
                colors.append('red')
                sizes.append(12)
            else:
                colors.append('blue')
                sizes.append(8)

            if idx != point_idx:
                # Only connect if the specific rotation matches
                if row["Spin Rotation"] == selected_spin:
                    spin_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                    spin_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                    if use_3d:
                        spin_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

                if row["Flip Rotation"] == selected_flip:
                    flip_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                    flip_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                    if use_3d:
                        flip_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

                # Add body rotation connections for 3D view
                if use_3d and row["Body Rotation"] == clicked_trick["Body Rotation"]:
                    body_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                    body_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                    body_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

        fig.data[0].marker.color = colors
        fig.data[0].marker.size = [s * 1.5 for s in sizes]
        fig.data[0].textfont = dict(size=8, color='black')

        if use_3d:
            if spin_line_x:
                fig.add_trace(go.Scatter3d(
                    x=spin_line_x,
                    y=spin_line_y,
                    z=spin_line_z,
                    mode='lines',
                    line=dict(color='green', width=3),
                    name='Spin Connection'
                ))
            if flip_line_x:
                fig.add_trace(go.Scatter3d(
                    x=flip_line_x,
                    y=flip_line_y,
                    z=flip_line_z,
                    mode='lines',
                    line=dict(color='magenta', width=3),
                    name='Flip Connection'
                ))
            if body_line_x:  # Add body rotation connections
                fig.add_trace(go.Scatter3d(
                    x=body_line_x,
                    y=body_line_y,
                    z=body_line_z,
                    mode='lines',
                    line=dict(color='orange', width=3),
                    name='Body Connection'
                ))
        else:
            if spin_line_x:
                fig.add_trace(go.Scatter(
                    x=spin_line_x,
                    y=spin_line_y,
                    mode='lines',
                    line=dict(color='green', width=3),
                    name='Spin Connection'
                ))
            if flip_line_x:
                fig.add_trace(go.Scatter(
                    x=flip_line_x,
                    y=flip_line_y,
                    mode='lines',
                    line=dict(color='magenta', width=3),
                    name='Flip Connection'
                ))

    return fig, info_content

if __name__ == '__main__':
    app.run_server(debug=True)
