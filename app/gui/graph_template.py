# app/gui/graph_template.py

GRAPH_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #282c34; overflow: hidden; font-family: sans-serif; }}
        #mynetwork {{ width: 100%; height: 100%; cursor: default; }}
        
        .watermark {{
            position: absolute; top: 10px; left: 10px; color: rgba(255,255,255,0.7); font-size: 14px; pointer-events: none; z-index: 10;
            background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;
        }}
        
        #loading {{
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: white; font-size: 16px; z-index: 20; background: rgba(0,0,0,0.8);
            padding: 15px; border-radius: 10px; display: block;
            width: 300px; text-align: center;
        }}
        #loading-bar-container {{
            height: 8px; background-color: #444; border-radius: 4px;
            margin-top: 10px; overflow: hidden;
        }}
        #loading-bar {{
            height: 100%; width: 0%; background-color: #61afef;
            transition: width 0.1s linear;
        }}

        /* --- Custom Tooltip Styling --- */
        #custom-tooltip {{
            position: absolute;
            display: none;
            background-color: #222; /* Dark background matching theme */
            color: #ddd;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px;
            font-size: 12px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            z-index: 9999;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.6);
            pointer-events: none; /* Allows mouse to pass through so it doesn't flicker */
            max-width: 450px;     /* Prevent extremely wide tables */
            line-height: 1.4;
        }}
    </style>
</head>
<body>
    <div class="watermark">{title}</div>
    
    <div id="loading">
        <span id="loading-text">Loading graph...</span>
        <div id="loading-bar-container">
            <div id="loading-bar"></div>
        </div>
    </div>

    <!-- The Graph Container -->
    <div id="mynetwork"></div>

    <!-- The Custom Tooltip Element -->
    <div id="custom-tooltip"></div>

    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var network;
        var chunkLoadingActive = {chunk_loading_js};

        window.addDataToGraph = function(newNodes, newEdges) {{
            try {{
                nodes.add(newNodes);
                edges.add(newEdges);
            }} catch (e) {{
                console.error("Failed to add data to graph:", e);
            }}
        }};
        
        window.showError = function(message) {{
            const loadingDiv = document.getElementById('loading');
            const textElement = document.getElementById('loading-text');
            const barContainer = document.getElementById('loading-bar-container');
            if (loadingDiv) loadingDiv.style.display = 'block';
            if (textElement) {{
                textElement.innerHTML = `<span style="color:#e06c75">Error</span><br><small>${{message}}</small>`;
            }}
            if (barContainer) barContainer.style.display = 'none';
        }};

        window.hideLoadingIndicator = function() {{
            const loadingDiv = document.getElementById('loading');
            if(loadingDiv) loadingDiv.style.display = 'none';
        }};

        window.updateLoadingProgress = function(current, total) {{
            const loadingDiv = document.getElementById('loading');
            if (total > 0 && current < total) {{
                loadingDiv.style.display = 'block';
                const percent = Math.round((current / total) * 100);
                const textElement = document.getElementById('loading-text');
                const barElement = document.getElementById('loading-bar');
                if (textElement) textElement.innerText = `Loading: ${{current}} / ${{total}}`;
                if (barElement) barElement.style.width = percent + '%';
            }}
        }};

        document.addEventListener("DOMContentLoaded", function () {{
            var container = document.getElementById('mynetwork');
            var tooltipEl = document.getElementById('custom-tooltip');
            var data = {{ nodes: nodes, edges: edges }};
            
            var options = {{
                nodes: {{ 
                    shape: 'dot', 
                    scaling: {{ min: 10, max: 30 }}, 
                    borderWidth: 2,
                    font: {{ color: '#eeeeee' }}
                }},
                edges: {{ 
                    smooth: {{ {edges_smooth} }}, 
                    color: {{ inherit: false, color: "#888", opacity: 0.4 }} 
                }},
                layout: {{ {layout_algo} }},
                physics: {{ {physics_config} }},
                interaction: {{ 
                    hover: true, 
                    // We set a huge delay so the default tooltip never shows up.
                    // We will handle it manually with 'hoverNode' event.
                    tooltipDelay: 3600000, 
                    hideEdgesOnDrag: {js_bool_is_massive} 
                }}
            }};
            
            if (nodes.length === 0) document.getElementById('loading').style.display = 'block';
            else document.getElementById('loading').style.display = 'none';
            
            network = new vis.Network(container, data, options);
            
            // --- Custom Tooltip Logic ---
            network.on("hoverNode", function (params) {{
                var nodeId = params.node;
                var node = nodes.get(nodeId);
                if (node && node.title) {{
                    // Inject HTML directly (bypassing Vis.js text rendering)
                    tooltipEl.innerHTML = node.title;
                    tooltipEl.style.display = 'block';
                    
                    // Position the tooltip near the node/cursor
                    // params.pointer.DOM gives coordinates relative to the canvas container
                    var domCoords = params.pointer.DOM;
                    tooltipEl.style.left = (domCoords.x + 15) + 'px';
                    tooltipEl.style.top = (domCoords.y + 15) + 'px';
                }}
            }});

            network.on("blurNode", function (params) {{
                tooltipEl.style.display = 'none';
            }});

            // Also update position on drag to prevent it sticking
            network.on("dragStart", function() {{ tooltipEl.style.display = 'none'; }});
            // ---------------------------

            var originalPositions = {{}};
            var captured = false;
            function captureBase() {{
                if (captured) return;
                var pos = network.getPositions();
                for (var id in pos) originalPositions[id] = pos[id];
                captured = true;
            }}

            network.on("stabilizationIterationsDone", function () {{
                if (!chunkLoadingActive) hideLoadingIndicator();
                network.setOptions({{ physics: false }});
                captureBase();
            }});
            
            if ({js_bool_is_massive} && !chunkLoadingActive) {{
                setTimeout(() => hideLoadingIndicator(), 100);
            }}

            window.applyExpansion = function(percent) {{
                if (!captured) captureBase();
                if (!captured) return;
                var scale = percent / 100.0;
                var updates = [];
                for (var id in originalPositions) {{
                    updates.push({{ id: id, x: originalPositions[id].x * scale, y: originalPositions[id].y * scale }});
                }}
                nodes.update(updates);
            }};

            new QWebChannel(qt.webChannelTransport, function (channel) {{
                window.bridge = channel.objects.bridge;
            }});
            
            network.on("click", function (params) {{
                if (params.nodes.length > 0 && window.bridge) window.bridge.js_callback(params.nodes[0]);
            }});

            network.on("oncontext", function (params) {{
                params.event.preventDefault();
                var nodeId = network.getNodeAt(params.pointer.DOM);
                if (nodeId && window.bridge) window.bridge.js_right_click(nodeId);
            }});
        }});
    </script>
</body>
</html>
"""