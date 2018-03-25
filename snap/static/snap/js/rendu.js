var grapheSvg, tree;
var actionsSvg;
document.addEventListener("DOMContentLoaded", function (e) {
    /* Your D3.js here */
    console.log("document prêt");
    initAffichages();
    initListeEleves();

});

/*
Set.prototype.union = function (setB) {
    var union = new Set(this);
    for (var elem of setB) {
        union.add(elem);
    }
    return union;
}*/
var margin = {
        top: 20,
        right: 20,
        bottom: 20,
        left: 20
    },
    width = "100%",
    height = 400,
    barHeight = 12,
    // barWidth = (width - margin.left - margin.right) * 0.8;
    barWidth = 100,
    scaleTime = 200;

var i = 0,
    duration = function (dragged) {
        return dragged ? 0 : 500;
    },
    root;

var diagonal = d3.linkHorizontal()
    .x(function (d) {
        return d.y;
    })
    .y(function (d) {
        return d.x;
    });

// Define Zoom Function Event Listener
function zoomFunction() {
    var transform = d3.zoomTransform(this);
    // console.log(this)
    // d3.select("#treesSvg")
    if (this.id == "affichageSvg")
        d3.select("#treesSvg")
        // .transition().duration(500)
        .attr("transform", "translate(" +
            (transform.x + 0) + "," + (transform.y + 0) +
            ") " +
            "scale(" + transform.k + ")");
    else
        d3.select(this)
        // .transition().duration(500)
        .attr("transform", "scale(" + transform.k + ")");
}

// Define Zoom Behavior
var zoom = d3.zoom()
    .scaleExtent([0.1, 20])
    .wheelDelta(function () {
        return -d3.event.deltaY * 10 / 500;
    })
    .on("zoom", zoomFunction);
var drag = d3.drag()


function initAffichages() {




    grapheSvg = d3.select("#affichage").append("svg")
        // .attr("preserveAspectRatio", "xMinYMin meet")
        // .attr("viewBox", "0 0 600 400")
        // class to make it responsive
        // .classed("svg-content-responsive", true)
        .attr("id", "affichageSvg")
        .attr("width", width) // + margin.left + margin.right)
        .attr("height", height)
        .attr("class", "graph-svg-component")

    grapheSvg.call(zoom)
        // .call(d3.zoom()
        // .on("zoom", function () {svg.attr("transform",
        // d3.event.transform)})
        .on("dblclick.zoom", function () {
            console.log("dezoom");
            // svg.attr("transform", "translate(" + margin.left + "," +
            // margin.top + ") scale(1)");
            grapheSvg.call(zoom.transform, d3.zoomIdentity);
        })
    /*
     * var a =
     * d3.scalePoint().domain(['Apples','Oranges','Pears','Plums']).range([0,500]);
     * var xAxis = d3.axisBottom(a); var svgGroup =
     * grapheSvg.append("g").attr("transform","translate(0,"+50+")");
     * svgGroup.append("text").attr("class","blue").attr("x","240").attr("y",0)
     * .attr("alignment-baseline","middle") .attr("text-anchor","end") .text('oula')
     * svgGroup.append("g").attr("transform","translate(270,0)").attr("class","axis").call(xAxis);
     */
    grapheSvg = grapheSvg.append("g").attr("id", "treesSvg");

    tree = grapheSvg.append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
        .attr("class", "tree1")


    actionsSvg = d3.select("#actions")
        .append("div").attr("id", "liste")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .call(zoom)
        .append("g")
        .attr("class", "actionG")

    d3.select("#liste").attr("align", "left")


}

function initListeEleves() {
    console.log('initialiation')
    d3.json('spropen/users', function (error, data) {
        console.info("reception liste elveves");
        console.log("reception", data);
        data.unshift({
            id: 0
        })
        var el = d3.select('#selectEleves')
        el.selectAll("option").data(data)
            .enter()
            .append("option")
            .attr("value", function (d) {
                return d.id
            })
            .text(function (d) {
                return d.id == 0 ? "---" : (d.username + "(" + (d.eleve ? d.eleve.classe : 'prof') + ")")
            })
        el.on("change", changeEleve)

    });
}

function changeEleve() {
    // var
    // selectedIndex=d3.select("#selectEleves").property('selectedOptions')[0].value
    var selectedValue = d3.select("#selectEleves").property('value')
    /*
     * var s=d3.select("#selectEleves").selectAll("option").filter(function
     * (d,i) { return d.id==selectedValue}), data=s.datum()
     * console.log('eke',data)
     */
    if (selectedValue != 0)
        d3.json('spropen/' + selectedValue + "/openUser", function (error, data) {
            console.log('data session', data);
            data.unshift({
                id: 0
            })
            var session = d3.select('#selectSessions')
            session.selectAll("option").data(data, function (d) {
                    return d.id
                })
                .enter()
                .append("option")
                .attr("value", function (d) {
                    return d.id
                })
                .text(function (d) {
                    return d.id == 0 ? "---" : ((new Date(d.evenement.creation)).toUTCString() + "(" + d.evenement.user + ")")
                })
            session.on("change", changeSession)
            // session.selectAll("option").call(function(d){console.log('update',d)})
            session.selectAll("option").data(data, function (d) {
                return d.id
            }).exit().remove()
        });
}

function changeSession() {
    var selectedValue = d3.select("#selectSessions").property('value')
    console.log('evnoi', selectedValue)
    getJson(selectedValue);
}

function getPrevNode(node) {
    // renvoie le noeud temporellement précédent, s'il existe
    if (node.data.time > 0) {
        n = root1.descendants()
            .filter(function (d) {
                return d.data.JMLid == node.data.JMLid && d.data.time < node.data.time;
            })
            .sort(function (a, b) {
                return a.data.time - b.data.time
            })
            .pop()
        return n
    }
    return undefined
}

function getLastParentId(node) {
    // renvoie l'id du noeud parent s'il existe,
    // ou l'id du noeud parent temporellement précédent s'il existe
    // ou l'id de la racine
    nodeId = node.conteneurBlock == null ? node.parentBlock : node.conteneurBlock
    if (nodeId != null) {
        n = donnees
            .filter(function (d) {
                return d.time <= node.time && (d.id == nodeId || d.JMLid == nodeId.split('_', 1)[0])
            })
            .sort(function (a, b) {
                return a.time - b.time
            })
            .pop()
        return n == undefined ? 'racine' : n.id
    }
    return null
}
var donnees = [],
    root1 = {},
    ticks = [],
    autresLinks = [],
    actions = [],
    data

function getJson(session) {
    if (session != 0) {
        console.log('session', session)
        d3.json("tb/" + session, function (error, data) {
            if (error) {
                console.warn("error", error.type, ":", error.target.statusText)
                return
            }
            /*
             * preparation des donnees: tous les blocks au temps 0, avec ajout
             * d'une racine fictive ajouts des blocks contenus en enfant des
             * blocks contenant
             */
            console.log('donnee recoes', data)
            donnees = data.data
            donnees.filter(function (d) {
                    return d.parentBlock == null && d.conteneurBlock == null
                })
                .forEach(function (d) {
                    d.parentBlock = 'racine'
                })
            ticks = data.ticks
            autresLinks = data.links
            actions = data.actions
            racine = {
                name: "racine",
                id: "racine",
                time: -1,
                rang: null,
                inputs: donnees.filter(function (d) {
                    return d.parentBlock == 'racine'
                })
            }
            // root1=d3.hierarchy(donnees,function children(d) {return
            // d.inputs;})
            donnees.push(racine)
            console.log(donnees, donnees.length)
            root1 = d3.stratify()
                .parentId(function (d) {
                    parentId = getLastParentId(d);
                    return parentId
                })
                (donnees)
            root1.x0 = 0;
            root1.y0 = 0;
            // calcul des coordonnées et ajout éventuel des liens avec le
            // prevNode
            root1._autresLinks = autresLinks
            var index = -1;
            var last = null
            /*
             * root1.sort(function(a,b) {return a.data.time-b.data.time ||
             * a.data.rang-b.data.rang}) .eachAfter(function(n) { n.JMLids=new
             * Set([n.data.JMLid]) if (n.height>0){
             * n.children.forEach(function(d)
             * {n.JMLids=n.JMLids.union(d.JMLids)}) } })
             */
            root1.sort(function (a, b) {
                    return a.data.time - b.data.time || a.data.rang - b.data.rang
                })
                .eachBefore(function (n) {
                    n.last = last
                    last = n
                    // if (!n.dragged) {
                    // calcul des coordonnées
                    p = getPrevNode(n)
                    if (n.data.lastModifBlock == null && p == undefined) {
                        n.x = ++index * barHeight;
                    } else if (n.data.lastModifBlock == null && p != undefined) {
                        if (n.parent.data.time == n.data.time) n.x = n.last.x + barHeight;
                        else n.x = n.parent.x + (n.data.rang + 1) * barHeight;
                    } else if (n.data.lastModifBlock != null) {
                        n.x = root1.descendants().filter(function (d) {
                            return d.id == n.data.lastModifBlock
                        })[0].x
                    }
                    n.y = n.depth * 10 + ticks.indexOf(n.data.time) * scaleTime;
                });

            root1.autresLinks = function () {
                // renvoie les liens entre prevNode et Node, s'ils sont visibles
                var edges = [];
                for (i in this._autresLinks) {
                    e = this._autresLinks[i];
                    var sourceNode = this.descendants().filter(function (n) {
                            return n.id === e.source;
                        })[0],
                        targetNode = this.descendants().filter(function (n) {
                            return n.id === e.target;
                        })[0];
                    if (sourceNode != undefined && targetNode != undefined) {
                        // Add the e</div>dge to the array
                        edges.push({
                            source: sourceNode,
                            target: targetNode,
                            type: e.type
                        });
                    }
                }
                // console.log('edges',edges)
                return edges;
            }
            update(root1, root1)

            updateListe(actions)
            updateEtapes(data.etapes, data.scripts)

        })
    } else {
        donnees = [];
        ticks = [];
        autresLinks = [];
        actions = [];

    }

}
var idex = 0,
    sizeHeight = 12,
    decalageFirst=20, //premiere ligne
    decalageNiveau=10, //decalge sur chaque niveau  (plutot que des caractères)
    spaceTime = 200

function updateEtapes(etapes, scripts) {
    etapesDiv = d3.select("#etapes")
        .append("svg")
        .attr("width", "100%")
        .attr("height", 200)
        .attr("opacity", 1)
    /*
     * on reconstruit les données sous la forme
     * [{time,action,commandes:[{index,scriptIt,numero,JMLid,niveau,commande}]}...]
     */
    data = etapes.map(function (d, index) {
        a = []
        for (k in d.commandes) {
            b = d.commandes[k]
            for (j in b) {
                a.push({
                    index: scripts.indexOf(parseInt(k)),
                    scriptId: parseInt(k),
                    numero: j,
                    id: b[j].id,
                    niveau: b[j].niveau,
                    commande: b[j].commande
                })
            }
        }
        return {
            time: d.time,
            action: d.action,
            commandes: a
        }
    })
    //console.log('data rendu', data)
    /*
     * etapes.forEach(function(d,index) { //d.y=index*sizeHeight;
     * d.x=index*spaceTime d.index=index })
     */
    // etapesEnter=etapesDiv.selectAll(".etape").data(etapes,function(d) {return
    // d.id?d.id:idex++})
    
    /*
    définition des gradients
    */
     var gradientPair = etapesDiv
        .append("linearGradient")
        .attr("y1", 0)
        .attr("y2", 0)
        .attr("x1", "0")
        .attr("x2", "50")
        .attr("id", "gradientPair")
        .attr("gradientUnits", "userSpaceOnUse");
    gradientPair
        .append("stop")
        .attr("offset", "0")
        .attr("stop-color", "green")
        .attr("stop-opacity", "0.5");
    gradientPair
        .append("stop")
        .attr("offset", "1")
        .attr("stop-opacity", "0");
    
    var gradientImpair = etapesDiv
        .append("linearGradient")
        .attr("y1", 0)
        .attr("y2", 0)
        .attr("x1", "0")
        .attr("x2", "50")
        .attr("id", "gradientImpair")
        .attr("gradientUnits", "userSpaceOnUse");
    gradientImpair
        .append("stop")
        .attr("offset", "0")
        .attr("stop-color", "blue")
        .attr("stop-opacity", "0.5");
    gradientImpair
        .append("stop")
        .attr("offset", "1")
        .attr("stop-opacity", "0");
    
    
    etapesEnter = etapesDiv.selectAll(".etape").data(data, function (d) {
            return d.id || (d.id = ++i);
        })
        .enter()
    etapesGroupe = etapesEnter.append("g")
        .attr("class", "etape")
        .attr("transform", function (d, index) {
            return "translate(" +
                index * scaleTime + "," +
                0 +
                ")";
        })
    etapesGroupe
        .append("text")
        .attr("class", "timeetape")
        .text(function (d) {
            return "(" + d.id + ")" + d.time
        })
        .attr("dy", sizeHeight - 1)
    // .call(function(d){console.log('d',d,d.node().data())})
    etapesGroupe.each(function (d, i) {
        //console.log('traitement', d, i)
        var coms = d3.select(this)
            .selectAll('.groupeetape')
            .data(d.commandes)
            .enter()
            .append("g").attr("class", "groupeetape");
        coms
            .append("rect")
            .attr("class", function (d) {
                return ((d.index % 2 == 0) ? "pair" : "impair");
            })
            .attr("y", function (d, j) {
                return j * sizeHeight+d.index*(sizeHeight/2) + decalageFirst
            })
            .attr("x",function(d) {return d.niveau*decalageNiveau})
            .attr("width", 50)
            .attr("height", sizeHeight)
            .attr("fill", "url(#gradient)");
        coms
            .append('text')
            .attr("class", "textetape " )
            .attr("dy", function (d, j) {
                return (j + 1) * sizeHeight+d.index*(sizeHeight/2)+ decalageFirst
            })
            .attr("dx",function(d) {return d.niveau*decalageNiveau})
            .text(function (e, j) {
                //console.log(j + ":" + e.numero + ":" + '.'.repeat(e.niveau) + e.commande)                
                //return e.index + '..'.repeat(e.niveau) + e.commande
                return e.commande
            })

    })

    etapesDiv.selectAll(".etape").exit().remove()

}

function updateListe(actions) {
    // affiche la liste des étapes
    /*
     * liste//.attr("viewBox", "0,0,900,420") .append("circle") .attr("cx", 25)
     * .attr("cy", 25) .attr("r", 25) .style("fill", "purple");
     */
    var min = d3.min(actions, function (d) {
        return d.evenement.numero
    }) - 1;
    console.log('min', min)
    /*
     * l=liste.selectAll("text").data(actions,function(d) {return d.time})
     * .enter() .append("text").text(function(d){return
     * "temps"+d.evenement.time+':'+d.type_display}) .attr("transform",
     * function(d) { return "translate(" + 20 + "," +
     * (d.evenement.numero-min)*30 + ")"; })
     */
    var rectHeight = 25,
        padding = 1

    var gradient = actionsSvg
        .append("linearGradient")
        .attr("y1", 0)
        .attr("y2", 0)
        .attr("x1", "0")
        .attr("x2", "100%")
        .attr("id", "gradient")
        .attr("gradientUnits", "userSpaceOnUse")

    gradient
        .append("stop")
        .attr("offset", "0")
        .attr("stop-color", "red")
        .attr("stop-opacity", "1");

    gradient
        .append("stop")
        .attr("offset", "0.5")
        .attr("stop-color", "white")
        .attr("stop-opacity", "0.1");

    var action = actionsSvg.selectAll(".action")
        .data(actions, function (d) {
            return d.id
        })
    var actionEnter = action.enter().append("g")
        .attr("class", function (d) {
            return "action " + d.evenement.type
        })
        .attr("transform", function (d) {
            return "translate(" +
                0 + "," +
                //(d.evenement.numero - min) * (rectHeight + padding) +
                (d.evenement.numero - min) * scaleTime +
                ")";
        })
        .style("opacity", 1)
    rect = actionEnter.append("rect")
        .attr("y", -rectHeight / 2)
        .attr("width", 0)
        .attr("height", rectHeight)
        .attr("fill", "url(#gradient)");

    actionEnter.append("text")
        .attr("class", "actiontext")
        .attr("dy", 3.5)
        .attr("dx", 5.5)
        .text(function (d) {
            return d.evenement.time + ':' + d.type_display
        })
    // obligé de mettre le calcul de la largeur après la création
    rect.transition().duration(500)
        .attr('width', "100%"
            /*function (d, i) {
            return d3.selectAll('.actiontext').filter(function (d, j) {
                    return i === j;
                })
                .node().getComputedTextLength() + 40; // 20 de décalage texte à droite
            }*/
        )
    actionEnter.call(function (d) {
        // ajustement de la taille du svg (bizarre?)
        //actionsSvg.attr("height", actionsSvg.node().getBBox().height + 40)
        //actionsSvg.select(".actionG").attr("transform","translate(-50,50)");
    })

    action.exit().remove()
    // ajustement de la taille du svg (bizarre?)
    //actionsSvg.attr("height", actionsSvg.node().getBBox().height + 40)
    actionsSvg.attr("height", "100%");
    console.info(d3.select(".actionG").node().getBBox())
    d3.select(".actionG").attr("transform", "rotate(-90,0,0) translate(" +(-1)*
        (d3.select("#liste svg").node().getBBox().height-30) + ",0)");
        
}








/*
 * root1._autresLinks=[{"source":2,"target":8}, {"source":3,"target":12}] };
 */


function draggedNode(d) {
    // console.log("drag",d.x,d.y,d3.event.x,d3.event.y)
    // d3.select(this).attr("x", d.x=d3.event.x).attr("y", d.y=d3.event.y);
    d.x0 = d.x = d3.event.y
    d.y0 = d.y = d3.event.x
    d.dragged = true
    ancestors = d.ancestors()
    update(d, ancestors[ancestors.length - 1], true);
    updateLinks(true);
}

function update(source, root, dragged = false) {
    // Compute the flattened node list.
    var nodes = root.descendants();

    // var height = Math.max(500, nodes.length * barHeight + margin.top +
    // margin.bottom);
    // var height=1000;
    d3.select("svg").transition()
        .duration(duration(dragged))
    // .attr("height", height);
    // .attr("height", "100%");

    d3.select(self.frameElement).transition()
        .duration(duration(dragged))
    // .style("height", height + "px");
    // .style("height","100%")

    // Compute the "layout". TODO https://github.com/d3/d3-hierarchy/issues/67


    // Update the nodes…

    var node = tree.selectAll(".node")
        .data(nodes, function (d) {
            return d.id || (d.id = ++i);
        })


    var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", function (d) {
            return "translate(" + source.y0 + "," + source.x0 + ")";
        })
        .style("opacity", 0)
    // .call(d3.drag().on("drag",draggedNode))

    var test = function (d) {
        // console.info('test',d)
    };
    // Enter any new nodes at the parent's previous position.
    nodeEnter.append("rect")
        // .attr("x",function(d) {console.log('rect',d); return 12;})
        .attr("y", -barHeight / 2)
        .attr("height", barHeight)
        .attr("width", barWidth)
        .style("fill", color)
        .style("opacity", opacity)
        .on("click", click)
        .call(test)
    // .call(d3.drag().on("drag",dragged));;

    nodeEnter.append("text")
        .attr("dy", 3.5)
        .attr("dx", 5.5)
        .style("opacity",function(d) { 
            if (!d.data.action) return 1;
            return d.data.action.indexOf('DEL')!=-1?d.data.action.indexOf('_REPLACE')!=-1?1:0:1;
        })
        .text(function (d) {
            return d.data.name+d.data.action;
        });

    // Transition nodes to their new position.
    nodeEnter.transition()
        .duration(duration(dragged))
        .attr("transform", function (d) {
            return "translate(" + d.y + "," + d.x + ")";
        })
        .style("opacity", opacityNode);

    node.transition()
        .duration(duration(dragged))
        .attr("transform", function (d) {
            return "translate(" + d.y + "," + d.x + ")";
        })
        //.style("opacity", 1)
        .select("rect")
        .style("fill", color)
        //.style("opacity", opacity)
        .style("opacity", opacityNode);

    // Transition exiting nodes to the parent's new position.
    node.exit().transition()
        .duration(duration(dragged))
        .attr("transform", function (d) {
            return "translate(" + source.y + "," + source.x + ")";
        })
        .style("opacity", 0)
        .remove();

    // Update the links…
    var link = tree.selectAll(".link")
        .data(root.links(), function (d) {
            return d.target.id;
        });

    // Enter any new links at the parent's previous position.
    link.enter().insert("path", "g")
        .attr("class", function (d) {return (d.source.id=="racine")?"linkRacine":"link"})
        .attr("d", function (d) {
            var o = {
                x: source.x0,
                y: source.y0
            };
            return diagonal({
                source: o,
                target: o
            });
        })
        .on("click", function (e) {
            console.log('source:', e.source.id, ' target:', e.target.id, e)
        })
        //.style("opacity",function(d) {return (d.source.id=="racine")?0:1})
        .transition()
        .duration(duration(dragged))
        .attr("d", diagonal);

    // Transition links to their new position.
    link.transition()
        .duration(duration(dragged))
        .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(duration(dragged))
        .attr("d", function (d) {
            var o = {
                x: source.x,
                y: source.y
            };
            return diagonal({
                source: o,
                target: o
            });
        })
        .remove();
    var lines = grapheSvg.selectAll('.autreslink')
        .data(root1.autresLinks(), function (d) {
            return d.target.id;
        })

    function xpos(d) {
        return (d.type == 'nextblock' || d.type=='inserted')  ? d.source.y : (d.source.y + barWidth)
    }

    function ypos(d) {
        return {
            debut: (d.type == 'nextblock'|| d.type=='inserted') ? (d.source.x - barHeight / 2) : d.source.x,
            fin: (d.type == 'nextblock' || d.type=='inserted')? (d.target.x + barHeight / 2) : d.target.x,
        }
    }
    lines.enter()
        .append('line')
        .attr("class", function (d) {
            return "autreslink " + d.type
        })
        .attr('x1', xpos)
        .attr('y1', function (d) {
            return ypos(d).debut
        })
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
        .style("opacity", 0)
        .transition().duration(duration(dragged))
        .attr('x2', function (d) {
            return d.target.y
        })
        .attr('y2', function (d) {
            return ypos(d).fin
        })
        .style("opacity", 01)

    lines.transition().duration(duration(dragged) * 2)
        .attr('x1', xpos)
        .attr('y1', function (d) {
            return d.source.x
        })
        .attr('x2', function (d) {
            return d.target.y
        })
        .attr('y2', function (d) {
            return d.target.x;
        })
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
        .style("opacity", 1)

    lines.exit()
        // .attr('x1',function(d){return 0})
        // .attr('y1',function(d){return 0})
        // .attr('x2',function(d){return 0 })
        // .attr('y2',function(d){return 0})
        .style("opacity", function (d) {
            return 0
        })
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
        .transition().duration(duration(dragged))
        .remove;

    // Stash the old positions for transition.
    root.each(function (d) {
        d.x0 = d.x;
        d.y0 = d.y;
    });
}


// Toggle children on click.
function click(d) {
    if (d.children) {
        d._children = d.children;
        d.children = null;
    } else {
        d.children = d._children;
        d._children = null;
    }
    ancestors = d.ancestors()
    update(d, ancestors[ancestors.length - 1]);
    console.log('click sur', d.id, d)
}

function opacityNode(d) {
    if (!d.data.action) return 1;
    return d.data.action.indexOf('DEL')!=-1?d.data.action.indexOf('_REPLACE')!=-1?1:0.2:1;
}

function opacity(d) {
    return d._children ? 1 : d.children ? 0.6 : 0.6;
}

function color(d) {
    //
    switch (d.data.typeMorph) {
        case "InputSlotMorph":
            return "#fd8d3c";
        case "ReporterBlockMorph":
            return "green";
        case "CSlotMorph":
            return "#3182bd";
        case "CommandBlockMorph":
            return "#c6dbef";
        default:
            return "pink";

    }
}
