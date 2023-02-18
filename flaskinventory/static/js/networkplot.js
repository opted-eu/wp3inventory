// decalarations

// font-awesome icons
const FontAwesome = {
    "website": "\uf0ac",
    "print": "\uf1ea",
    "instagram": "\ue055",
    "facebook": "\uf09a",
    "twitter": "\uf099",
    "vkontakte": "\uf189",
    "telegram": "\uf2c6"

}

function recurseData(data) {
    // known limitations:
    // 1) does not have any limits, so it will parse the data regardless of its total length 
    // can only parse list (Array) relationsships, ignores 1-1 relationships (Object)

    let nodes = []
    let edges = []
    let heap_nodes = []
    let heap_edges = []
    for(let node of data) {
        if (!heap_nodes.includes(node.uid)) {
            heap_nodes.push(node.uid)
            nodes.push({id: node.uid, 
                        uid: node.uid, 
                        name: node.name, 
                        type: node['dgraph.type'].pop('Entry'), 
                        channel: node.channel?.unique_name
                        })
        }
        for (let key of Object.keys(node)) {
            if (Array.isArray(node[key])) {
                for (let child of node[key]) {
                    if (Object.keys(child).includes('uid')) {
                        let edge = ''
                        if (key.startsWith('~')) {
                            edge = `${child.uid}_${node.uid}`
                        } else {
                            edge = `${node.uid}_${child.uid}`
                        }
                        if (!heap_edges.includes(edge)) {
                            heap_edges.push(edge)
                            if (key.startsWith('~')) {
                                edges.push({ id: edge, source: child.uid, target: node.uid, relationship: key.replace('~', '') })
                            } else {
                                edges.push({ id: edge, source: node.uid, target: child.uid, relationship: key })
                            }
                        }

                    }
                }
            }
        }
    }

  return { 'nodes': nodes, 'edges': edges, '_heap_nodes': heap_nodes, '_heap_edges': heap_edges }
}


function parseNodes(rawjson) {

    // sorting produces slightly better graph rendering
    function sortByType(a, b) {
        if (a.type > b.type) return 1;
        if (a.type < b.type) return -1;
        return 0;
    }

    function sortByRelationship(a, b) {
        if (a.relationship > b.relationship) return 1;
        if (a.relationship < b.relationship) return -1;
        return 0;
    }

    let recursed = recurseData(rawjson)
    let n = recursed.nodes.sort(sortByType);
    let e = recursed.edges.sort(sortByRelationship);


    let output = {
        nodes: n,
        links: e
    }
    return output
}


// Draw Network Function

function drawChart({
    links,
    nodes
},
    {
        width = 400,
        height = 600,
        color = "#495057",
        nodeRadius = 15,
        forceStrength = -500,
        invalidation = null
    } = {}) {

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(30))
        .force("charge", d3.forceManyBody().strength(forceStrength))
        .force("x", d3.forceX())
        .force("y", d3.forceY());
        // .force("bounds", boxingForce);

    const svg = d3.create("svg")
        .attr("version", "1.1")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [-width / 2 - nodeRadius*2, -height / 2, width -nodeRadius*2, height])
        .attr("style", "max-width: 100%; height: auto; height: intrinsic;");


    // Per-type markers, as they don't inherit styles.
    svg.append("defs").selectAll("marker")
        .data(links)
        .join("marker")
        .attr("id", d => `arrow-${d.index}`)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", function(d) {
            let arrowSize = 7
            if (d.target.type == 'Organization') {
                return nodeRadius*1.2 + arrowSize
            } else {
                return nodeRadius + arrowSize
            }
        })
        .attr("refY", 0)
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .attr("orient", "auto")
        .append("path")
        .attr("fill", color)
        .attr("d", "M0,-5L10,0L0,5");

    const link = svg.append("g")
        .attr("fill", "none")
        .attr("stroke-width", 1.5)
        .selectAll("path")
        .data(links)
        .join("path")
        .attr("stroke", color)
        .attr("marker-end", d => `url(${new URL(`#arrow-${d.index}`, location)})`);

    const node = svg.append("g")
        .attr("fill", "currentColor")
        .attr("stroke-linecap", "round")
        .attr("stroke-linejoin", "round")
        .selectAll("a")
        .data(nodes)
        .join("a")
        .attr("href", d => `${$SCRIPT_ROOT}/view?uid=${d.uid}`)
        .attr("class", d => `node-type-${d.type}`)
        .classed('node-group', true)
        .classed('text-decoration-none', true)
        .call(drag(simulation));

    node.append("circle")
        .attr("stroke", "white")
        .attr("stroke-width", 1.5)
        .attr("r", function (d) {
            if (d.type == 'Organization') {
                return nodeRadius * 1.2
            } else {
                return nodeRadius
            }
        })
        .attr("class", d => d.type)
        .classed("currentNode", d => d.uid === data.uid)
           

    // render channel-icon
    // one day group according to channel: https://bl.ocks.org/GerHobbelt/3104394
    node.selectAll(".Source")
        .each(function(d) {
            this.classList.add("color-" + d.channel);
        });
        // .each(d => this.classList.add(`color-${d.channel}`))
        // .attr("class", function (d) {
        //     d3.select(this).attr("class") + " node" + d.id;
        // })
        // .attr("class", d => `color-${d.channel}`)

    svg.selectAll(".node-type-Source")
        .append("text")
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .style('font-family', function (d) {
            if (['print', 'website'].includes(d.channel)) { return '"Font Awesome 5 Free"' }
            else { return '"Font Awesome 5 Brands"' }
        })
        .style('color', 'white')
        .style('fill', 'white')
        .text(d => FontAwesome[d.channel]);

    node.append("title")
        .text(d => `${d.name} (${d.type})`)

    node.append("text")
        .attr("x", 0)
        .attr("y", nodeRadius * 2)
        .attr('text-anchor', 'middle')
        .classed('nodeLabel', true)
        .text(d => truncate(d.name))
        .clone(true).lower()
        .attr("fill", "none")
        .attr("stroke", "white")
        .attr("stroke-width", 3);

    node.selectAll("text").raise()

    // helper functions

    function linkArc(d) {
        const r = Math.hypot(d.target.x - d.source.x, d.target.y - d.source.y);
        return `
                  M${d.source.x},${d.source.y}
                  A${r},${r} 0 0,1 ${d.target.x},${d.target.y}
              `;
    };

    function truncate(input) {
        if (input.length > 25) {
            return input.substring(0, 25) + '...';
        }
        return input;
    };


    // simulation functions

    function boxingForce() {
        const radius = width;

        for (let node of nodes) {
            // Of the positions exceed the box, set them to the boundary position.
            // You may want to include your nodes width to not overlap with the box.
            node.x = Math.max(-radius, Math.min(radius, node.x));
            node.y = Math.max(-radius, Math.min(radius, node.y));
        }
    }

    function drag(simulation) {

        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    simulation.on("tick", () => {
        // if links should be arcs use this function
        // note to adjust refY to move arrow head
        // link.attr("d", linkArc);
        
        link.attr("d", function (d) {
            return `        
              M${d.source.x},${d.source.y}
              L ${d.target.x},${d.target.y}
              `
        });
        node.attr("transform", function (d) {

            return `translate(${d.x},${d.y})`
        });

    });

    // wait some ticks and then resize
    const t = d3.timer((elapsed) => {
        if (elapsed > 500) { 
            t.stop()
            let bbox = d3.select('#network-plot svg').node().getBBox();
            console.log(bbox)
            svg.
                transition().duration(400).
                attr("viewBox", `${bbox.x},${bbox.y-nodeRadius*2},${bbox.width+nodeRadius*2},${bbox.height+nodeRadius*2}`)
            };
      }, 150);

    if (invalidation != null) invalidation.then(() => simulation.stop());

    return svg.node();
}


function MakeNetworkPlot(uid, endpoint, divId) {

    document.addEventListener("DOMContentLoaded", function () {

        const plotArea = document.getElementById(divId)
        const plotWidth = plotArea.parentElement.clientWidth

        fetch(endpoint, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(uid),
        })
            .then((response) => response.json())
            .then((data) => parseNodes(data))
            .then((network) => drawChart(network, {width: plotWidth, height:  plotWidth}))
            .then((plot) => plotArea.appendChild(plot))
            .then(function () {
                // ensure that hovered elements are on top
                d3.selectAll(`#${divId} a`).on("mouseenter", function () {
                    d3.select(this).raise();
                });

                // zoom
                let zoom = d3.zoom()
                    .on('zoom', handleZoom);

                function handleZoom(e) {
                    d3.selectAll('svg g')
                        .attr('transform', e.transform);
                }

                function initZoom() {
                    d3.select('svg')
                        .call(zoom);
                }

                initZoom()
            })
            .catch((error) => {
                console.error('Error:', error);
            });


    });
}
