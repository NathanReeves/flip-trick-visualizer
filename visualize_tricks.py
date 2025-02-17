import io
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go

# Read CSV while ignoring commented lines.
df = pd.read_csv("trick_names.csv", comment='#', skip_blank_lines=True)
df['Trick Name'] = df['Trick Name'].str.strip()

# --- Build the Dash App ---
app = Dash(__name__)
app.layout = html.Div([
    html.H1("Skateboarding Flatground Flip Tricks Visualization"),
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
    ], style={'padding': '10px'}),
    # Hidden store to keep track of the latest camera settings
    dcc.Store(id="camera-store"),
    dcc.Graph(id='trick-graph'),
    html.Div(id='trick-info', style={
        'padding': '10px',
        'border': '1px solid #ccc',
        'margin-top': '10px'
    })
])

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

# --- Callback to update the graph and info panel, preserving camera ---
@app.callback(
    [Output('trick-graph', 'figure'),
     Output('trick-info', 'children')],
    [Input('view-toggle', 'value'),
     Input('trick-graph', 'clickData')],
    [State('camera-store', 'data')]
)
def update_graph(view, clickData, stored_camera):
    if view == '3D':
        scatter = go.Scatter3d(
            x=df['Spin Rotation'],
            y=df['Flip Rotation'],
            z=df['Body Rotation'],
            mode='markers',
            marker=dict(size=8, color='blue', opacity=0.8),
            text=df['Trick Name'],
            customdata=df[['Spin Rotation', 'Flip Rotation', 'Body Rotation', 'Trick Name']].values,
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<br>' +
                'Body Rotation: %{z}<extra></extra>'
            )
        )
        fig = go.Figure(data=[scatter])
        scene_layout = dict(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            zaxis_title='Body Rotation'
        )
        if stored_camera:
            scene_layout["camera"] = stored_camera
        fig.update_layout(
            scene=scene_layout,
            margin=dict(l=0, r=0, b=0, t=0),
            uirevision="constant",  # Preserve UI state across updates
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right',
            )
        )
    else:
        scatter = go.Scatter(
            x=df['Spin Rotation'],
            y=df['Flip Rotation'],
            mode='markers',
            marker=dict(size=8, color='blue', opacity=0.8),
            text=df['Trick Name'],
            customdata=df[['Spin Rotation', 'Flip Rotation', 'Body Rotation', 'Trick Name']].values,
            hovertemplate=(
                'Trick: %{text}<br>' +
                'Spin Rotation: %{x}<br>' +
                'Flip Rotation: %{y}<extra></extra>'
            )
        )
        fig = go.Figure(data=[scatter])
        fig.update_layout(
            xaxis_title='Spin Rotation',
            yaxis_title='Flip Rotation',
            margin=dict(l=0, r=0, b=0, t=0),
            uirevision="constant",
            legend=dict(
                font=dict(size=12),
                itemsizing='constant',
                itemwidth=30,
                x=1.0,
                xanchor='right',
            )
        )
    
    # Default info message
    info_content = html.Div("Click on a trick to get more information.", style={'font-style': 'italic'})
    
    # If a trick is clicked, update the info panel, highlight similar tricks, and add connection lines.
    if clickData is not None:
        point_data = clickData['points'][0]
        point_idx = point_data.get('pointIndex', point_data.get('pointNumber'))
        if point_idx is not None:
            clicked_trick = df.iloc[point_idx]
            selected_spin = clicked_trick["Spin Rotation"]
            selected_flip = clicked_trick["Flip Rotation"]

            info_content = html.Div([
                html.H4(clicked_trick["Trick Name"]),
                html.P(f"Spin Rotation: {clicked_trick['Spin Rotation']}"),
                html.P(f"Flip Rotation: {clicked_trick['Flip Rotation']}"),
                html.P(f"Body Rotation: {clicked_trick['Body Rotation']}")
            ])

            colors = []
            sizes = []
            spin_line_x, spin_line_y, spin_line_z = [], [], []
            flip_line_x, flip_line_y, flip_line_z = [], [], []
            for idx, row in df.iterrows():
                if (row["Spin Rotation"] == selected_spin) or (row["Flip Rotation"] == selected_flip):
                    colors.append('red')
                    sizes.append(12)
                else:
                    colors.append('blue')
                    sizes.append(8)
                if idx != point_idx:
                    if row["Spin Rotation"] == selected_spin:
                        spin_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                        spin_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                        if view == '3D':
                            spin_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]
                    if row["Flip Rotation"] == selected_flip:
                        flip_line_x += [clicked_trick["Spin Rotation"], row["Spin Rotation"], None]
                        flip_line_y += [clicked_trick["Flip Rotation"], row["Flip Rotation"], None]
                        if view == '3D':
                            flip_line_z += [clicked_trick["Body Rotation"], row["Body Rotation"], None]
            # Update marker styling and add connection lines.
            fig.data[0].marker.color = colors
            fig.data[0].marker.size = sizes

            if view == '3D':
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
