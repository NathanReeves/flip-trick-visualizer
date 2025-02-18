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
            'marginleft': '10px',
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
    use_3d = view == '3D'
    
    # Use cached dataframe
    global df_2d, df_3d
    data_df = df_3d if use_3d else df_2d
    
    # Modified marker settings to account for asterisk
    def get_marker_color(row):
        if pd.isna(row['Trick Name']):
            return 'lightgray'
        elif row['Has_Asterisk']:
            return 'purple'  # Different color for tricks with asterisk
        else:
            return 'blue'
    
    marker_settings = dict(
        size=[20 if pd.notna(name) else 8 for name in data_df['Trick Name']],
        color=[get_marker_color(row) for _, row in data_df.iterrows()],
        opacity=0.6
    )
    
    if use_3d:
        scatter = go.Scatter3d(
            x=data_df['Spin Rotation'],
            y=data_df['Flip Rotation'],
            z=data_df['Body Rotation'],
            mode='markers+text',
            marker=marker_settings,
            text=data_df['Trick Name'],
            textposition='top center',
            textfont=dict(
                size=8,
                color='black'  # Changed to show all text by default
            ),
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<br>' +
                'Body Rotation: %{z}<extra></extra>'
            ),
            name='Confirmed Tricks',
            legendgroup='tricks',
            showlegend=True
        )
    else:
        scatter = go.Scatter(
            x=data_df['Spin Rotation'],
            y=data_df['Flip Rotation'],
            mode='markers+text',
            marker=marker_settings,
            text=data_df['Trick Name'],
            textposition='top center',
            textfont=dict(
                size=8,
                color='black'
            ),
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<extra></extra>'
            ),
            name='Confirmed Tricks',
            legendgroup='tricks',
            showlegend=True
        )

    fig = go.Figure(data=[scatter])
    
    # Simplified layout
    layout_settings = dict(
        margin=dict(l=0, r=0, b=0, t=0),
        uirevision="constant",
        showlegend=True,
        legend=dict(
            font=dict(size=12),
            itemsizing='constant',
            itemwidth=30,
            x=1.0,
            xanchor='right',
            y=0.98,  # Shift down from default 1.0
            yanchor='top'
        )
    )
    
    if use_3d:
        scene_layout = dict(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            zaxis_title='Body Rotation',
            # Simplified tick settings
            xaxis=dict(tickmode='linear', dtick=180),
            yaxis=dict(tickmode='linear', dtick=360),
            zaxis=dict(tickmode='linear', dtick=180),
        )
        if stored_camera:
            scene_layout["camera"] = stored_camera
        layout_settings["scene"] = scene_layout
    else:
        layout_settings.update(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            xaxis=dict(tickmode='linear', dtick=180),
            yaxis=dict(tickmode='linear', dtick=360)
        )
    
    fig.update_layout(**layout_settings)

    # Add dummy traces for legend items
    fig.add_trace(go.Scatter3d(
        x=[None], y=[None], z=[None],
        mode='markers',
        marker=dict(size=20, color='purple', opacity=0.6),
        name='Unconfirmed Tricks',
        showlegend=True
    ) if use_3d else go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=20, color='purple', opacity=0.6),
        name='Unconfirmed Tricks',
        showlegend=True
    ))

    # Process click data only if present
    info_content = html.Div("Click on a trick to get more information.", 
                           style={'fontStyle': 'italic'})
    
    if clickData is not None:
        # Hide the legend items for regular/unconfirmed tricks
        fig.data[0].showlegend = False  # Hide regular tricks legend
        fig.data[1].showlegend = False  # Hide unconfirmed tricks legend
        
        point_data = clickData['points'][0]
        point_idx = point_data.get('pointIndex', point_data.get('pointNumber'))
        
        # Get the trick name from the previous view's dataframe
        prev_df = df_3d if point_data.get('z') is not None else df_2d
        if point_idx is not None and point_idx < len(prev_df):
            trick_name = prev_df.iloc[point_idx]["Trick Name"]
            # Find the corresponding trick in the current view's dataframe
            trick_mask = data_df["Trick Name"] == trick_name
            if trick_mask.any():
                clicked_trick = data_df[trick_mask].iloc[0]
                selected_spin = clicked_trick["Spin Rotation"]
                selected_flip = clicked_trick["Flip Rotation"]

                # Build the info panel.
                # Determine spin direction
                spin_direction = "Backside" if clicked_trick['Spin Rotation'] < 0 else "Frontside" if clicked_trick['Spin Rotation'] > 0 else ""
                
                info_items = [
                    html.H4(clicked_trick["Trick Name"]),
                    html.P(f"Spin Rotation: {clicked_trick['Spin Rotation']}")
                ]
                info_items.extend([
                    html.P(f"Flip Rotation: {clicked_trick['Flip Rotation']}")
                ])
                if use_3d:
                    info_items.append(html.P(f"Body Rotation: {clicked_trick['Body Rotation']}"))

                                    # Add spin direction if there is rotation
                if spin_direction:
                    info_items.append(html.P(f"Direction: {spin_direction}"))
                
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
                    if (row["Spin Rotation"] == selected_spin and row["Spin Rotation"] != 0 or 
                        row["Flip Rotation"] == selected_flip and row["Flip Rotation"] != 0 or 
                        (use_3d and row["Body Rotation"] == clicked_trick["Body Rotation"] and row["Body Rotation"] != 0)):
                        colors.append('red')
                        sizes.append(15)
                    elif pd.notna(row["Trick Name"]) and row["Trick Name"].strip():
                        colors.append('lightgray')
                        sizes.append(8)
                    else:
                        colors.append('lightgray')
                        sizes.append(8)

                    if idx != point_idx:
                        # Only connect if the specific rotation matches
                        if row["Spin Rotation"] == selected_spin and row["Spin Rotation"] != 0:
                            spin_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                            spin_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                            if use_3d:
                                spin_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

                        if row["Flip Rotation"] == selected_flip and row["Flip Rotation"] != 0:
                            flip_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                            flip_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                            if use_3d:
                                flip_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

                        # Add body rotation connections for 3D view
                        if use_3d and row["Body Rotation"] == clicked_trick["Body Rotation"] and row["Body Rotation"] != 0:
                            body_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                            body_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                            body_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]

                fig.data[0].marker.color = colors
                fig.data[0].marker.size = [s * 1.5 for s in sizes]
                
                # Update text visibility only when a point is clicked
                text_colors = ['black'] * len(data_df)  # Start with all visible
                if clickData is not None:  # Only modify colors if a point is clicked
                    text_colors = ['rgba(0,0,0,0)'] * len(data_df)  # Hide all first
                    for i, color in enumerate(colors):
                        if color == 'red':  # Show text only for selected tricks
                            text_colors[i] = 'black'
                fig.data[0].textfont.color = text_colors

                if use_3d:
                    if spin_line_x:
                        fig.add_trace(go.Scatter3d(
                            x=spin_line_x,
                            y=spin_line_y,
                            z=spin_line_z,
                            mode='lines',
                            line=dict(color='green', width=3),
                            name='Spin Connection',
                            hoverinfo='skip'
                        ))
                    if flip_line_x:
                        fig.add_trace(go.Scatter3d(
                            x=flip_line_x,
                            y=flip_line_y,
                            z=flip_line_z,
                            mode='lines',
                            line=dict(color='magenta', width=3),
                            name='Flip Connection',
                            hoverinfo='skip'
                        ))
                    if body_line_x:  # Add body rotation connections
                        fig.add_trace(go.Scatter3d(
                            x=body_line_x,
                            y=body_line_y,
                            z=body_line_z,
                            mode='lines',
                            line=dict(color='orange', width=3),
                            name='Body Connection',
                            hoverinfo='skip'
                        ))
                else:
                    if spin_line_x:
                        fig.add_trace(go.Scatter(
                            x=spin_line_x,
                            y=spin_line_y,
                            mode='lines',
                            line=dict(color='green', width=3),
                            name='Spin Connection',
                            hoverinfo='skip'
                        ))
                    if flip_line_x:
                        fig.add_trace(go.Scatter(
                            x=flip_line_x,
                            y=flip_line_y,
                            mode='lines',
                            line=dict(color='magenta', width=3),
                            name='Flip Connection',
                            hoverinfo='skip'
                        ))
    else:
        # Show the legend items when no trick is selected
        fig.data[0].showlegend = True
        fig.data[1].showlegend = True

    return fig, info_content

if __name__ == '__main__':
    # Load and cache dataframes
    df = pd.read_csv("trick_names.csv", comment='#', skip_blank_lines=True)
    df['Trick Name'] = df['Trick Name'].str.strip()
    
    # Add a column to track if the trick has an asterisk
    df['Has_Asterisk'] = df['Trick Name'].str.contains(r'\*')
    
    # Remove text within parentheses and asterisks, then strip whitespace
    df['Trick Name'] = df['Trick Name'].str.replace(r'\s*\([^)]*\)', '', regex=True)
    df['Trick Name'] = df['Trick Name'].str.replace(r'\*', '', regex=True).str.strip()
    
    # Cache 2D and 3D dataframes
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
