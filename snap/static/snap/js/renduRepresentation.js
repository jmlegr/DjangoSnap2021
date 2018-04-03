var widthPpal = 1000,
    heightPpal = d3.select("#affichage").node().getBoundingClientRect().height,
    heightAction = 100, //hauteur de la vue globale des actions (+actionSvg.attr("height"));
    heightArbre=350; //hateur de la vue arbre
    

var affichageSvg, // l'affichage arbre+script
    ligneActionSvg, //ligne et indication des actions
    arbreSvg, // afficahge arbre    
    affichageActionNode, //noeud avec les data d'actions
    scriptSvg, //emplacement le reconstitution des scripts
    actionSvg, // actions
    margin = {
        top: 0,
        right: 0,
        bottom: 0,
        left: 0
    }, //pour arbre
    margin2 = {
        top: heightArbre,
        right: 0,
        bottom: 0,
        left: 0
    }, //pour scripts
    width = widthPpal- margin.left - margin.right, //+affichageSvg.attr("width") 
    height = heightPpal - margin.top - margin.bottom, //+affichageSvg.attr("height")
    height2 = heightPpal - margin2.top - margin2.bottom // +affichageSvg.attr("height") enlever la position de xaxis 
    
var x = d3.scaleLinear().range([0, width]),
    x2 = d3.scaleLinear().range([0, width]);

var xAxis = d3.axisBottom(x),
    xAxis2 = d3.axisBottom(x2);

var brush = d3.brushX().extent([[0, 0], [width, heightAction]]).on(
    "brush end", brushed);

var zoom = d3.zoom().scaleExtent([1, Infinity]).translateExtent(
	[[0, 0], [width, height + height2]]).extent(
	[[0, 0], [width, height + height2]]).on("zoom", zoomed);


initSvg();
initListeEleves();


function initSvg() {
    //initialise les svg de base
    
    // l'affichage arbre+script
    affichageSvg = d3.select("#affichage")
        .append("svg")
        .attr("id","affichageSvg")
        .attr("width", widthPpal) // + margin.left + margin.right)
        .attr("height", heightPpal)
        //.attr("class", "graph-svg-component"), 
    //ajout du clp path pour l'affichage
    affichageSvg.append("defs")
        .append("clipPath").attr("id", "clip")
            .append("rect").attr("width", width).attr("height", heightPpal + 20);   
    // zoom sur l'affichage (brush) (ici pour être sous les autres éléments)
    var zoomSvg=affichageSvg.append("rect")
    .attr("class", "zoomEW")
    .attr("width", width)
    .attr("height", height)
    .attr("transform", "translate(" + margin.left + "," +
        margin.top + ")")
    .call(zoom);
    //lignes et indication des action
    ligneActionSvg = affichageSvg.append("g").attr("class","ligneAction")
    //arbre
    arbreSvg = affichageSvg
        .append("g")
        .attr("class", "arbre")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
    //scripts
    scriptSvg = affichageSvg.append("svg").attr("height",height2) //affichage scripts 
    .attr("class", "scripts").attr("transform",
        "translate(" + margin2.left + "," + margin2.top + ")")
    
    //affichage global des actions en bas
    actionSvg = d3.select("#actions")
        .append("svg")
        .attr("class", "actions")
        .attr("id", "actionSvg")
        .attr("width", widthPpal)
        .attr("height", heightAction) //affichage actions
        
    // on initialise les axes le brush et le zoom (pour ne pas les rajouter à chaque chargement)        
    
    actionSvg
        .append("g")
        .attr("class", "axis axis--x")
        .attr("transform","translate(0," + (actionSvg.attr("height") / 2) + ")").call(xAxis2);
    actionSvg
        .append("g")
        .attr("class", "brush actionNode")
        .call(brush)
        .call(brush.move, x.range());
    affichageSvg.append("g").attr("class", "axis axis--x").attr("transform",
    "translate(0," + (heightPpal - 20) + ")").call(xAxis);    
}

function initListeEleves() {
    //initialisation de la liste des élèves
    console.log('initialiation')
    d3.json('spropen/users', function (error, data) {
        console.log("reception", data);
        data.unshift({
            id: 0
        })
        var el = d3.select('#selectEleves')
        el.selectAll("option").data(data).enter().append("option").attr(
            "value",
            function (d) {
                return d.id
            }).text(
            function (d) {
                return d.id == 0 ? "---" : (d.username + "(" +
                    (d.eleve ? d.eleve.classe : 'prof') + ")")
            })        
        el.on("change", initSessions)
    });
}

function initSessions() {
    //récupération de la liste des sessions
    var selectedValue = d3.select("#selectEleves").property('value')
    if (selectedValue != 0)
        d3.json('spropen/' + selectedValue + "/openUser",
            function (error, data) {
                console.log('data session', data);
                data.unshift({
                    id: 0
                })
                var session = d3.select('#selectSessions')
                session.selectAll("option").data(data, function (d) {
                    return d.id
                }).enter().append("option").attr("value", function (d) {
                    return d.id
                }).text(
                    function (d) {
                        return d.id == 0 ? "---" : ((new Date(
                                d.evenement.creation)).toUTCString() +
                            "(" + d.evenement.user + ")")
                    })
                session.on("change", chargeSession)
                session.selectAll("option").data(data, d=>d.id).exit().remove()
            });
}

function chargeSession() {
    var selectedValue = d3.select("#selectSessions").property('value')
    getJson(selectedValue);
}

function getLastParentId(node) {
    // renvoie l'id du noeud parent s'il existe,
    // ou l'id du noeud parent temporellement précédent s'il existe
    // ou l'id de la racine
    nodeId = node.conteneurBlock == null ? node.parentBlock :
        node.conteneurBlock
    if (nodeId != null) {
        n = donnees.filter(
            function (d) {
                return d.time <= node.time &&
                    (d.id == nodeId || d.JMLid == nodeId.split('_',
                        1)[0])
            }).sort(function (a, b) {
            return a.time - b.time
        }).pop()
        return n == undefined ? 'racine' : n.id
    }
    return null
}

//objet ticks, pour scale.
//note: si on veut un scale linéaire et temporel if fau redéfinir invert comme x2.invert() (àtester)
var ticks = {
    times: [],
    invert: function (d) {
        var r = this.times.indexOf(d);
        if (r != -1)
            return r;
        //c'est un ticks correspondant à un évènement autre que SPR
        for (i in this.times) {
            if (this.times[i] > d) {
                return (i - 1 + (d - this.times[i - 1]) / (this.times[i] - this.times[i - 1]))
            }
        }
        return this.length();
    },
    length: function () {
        return this.times.length
    }
}

function tooltip(selection,html,duration=200) {
    //affichage d'un tooltip sur la selection
    //usage: selection.call(tooltip,"texte html" [,durée])
    var divTooltip = d3.select("#tooltip").attr("class", "tooltip").style("opacity", 0);
    console.log("html!",html,"select",selection)
     return selection.on(
         "mouseover",
         function (d) {
             divTooltip.transition()
                 .duration(duration).style("opacity", .9);
             divTooltip
                 .html(html)
                 .style("left", (d3.event.pageX) + "px")
                 .style("top", (d3.event.pageY - 28) + "px");
         }).on(
         "mouseout",
         "mouseout",
         function (d) {
             divTooltip.transition()
                 .duration(500).style("opacity", 0);
         });
}

function getJson(session) {
    if (session != 0) {
        console.log('session', session)
        d3
            .json(
                "tb/" + session,
                function (error, data) {
                    if (error) {
                        console.warn("error", error.type, ":",
                            error.target.statusText)
                        return

                    }
                    /*
                     * preparation des donnees: tous les blocks au temps 0, avec ajout
                     * d'une racine fictive ajouts des blocks contenus en enfant des
                     * blocks contenant
                     */
                    console.log('donnee recoes', data)
                    donnees = data.data
                    ticks.times = data.ticks
                    links = data.links
                    actions = data.actions
                    //extent=d3.extent(actions, function(d) { return d.evenement.time; })
                    //extent[1]+=10000
                    //x.domain(extent);
                    x.domain([0, ticks.length()])
                    x2.domain(x.domain());
                    //on chage pour tester: ordinal

                    // construction des axes
                    actionSvg.selectAll("g.axis")
                        .attr("class","axis axis--x")
                        .attr("transform", "translate(0," + actionSvg.attr("height")/2 + ")")
                        .call(xAxis2);
                    affichageSvg.selectAll("g.axis")
                        .attr("class","axis axis--x")
                        .attr("transform","translate(0," + (heightPpal - 20) + ")")
                        .call(xAxis);
                    
                    //brush
                    actionSvg.selectAll("g.brush").attr("class",
                        "brush actionNode").call(brush).call(
                        brush.move, x.range());
                    // actions dans actionSvg
                    setActions(actions)
                    //préparation des scripts
                    /*
                     * 	on reconstruit les données sous la forme
                     * 	[{time,action,commandes:[{index,scriptIt,numero,Jhttps://github.com/d3/d3-zoom#zoom_onMLid,niveau,commande}]}...]
                     */
                    etapes = data.etapes.map(function (d, index) {
                        a = []
                        for (k in d.commandes) {
                            b = d.commandes[k]
                            for (j in b) {
                                a.push({
                                    index: data.scripts
                                        .indexOf(parseInt(k)),
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
                    var idex = 0,
                        sizeHeight = 12,
                        decalageFirst = 20, //premiere ligne
                        decalageNiveau = 10, //decalge sur chaque niveau  (plutot que des caractères)  ,
                        etapesSvg = scriptSvg.selectAll(".etape").data(
                            etapes,
                            function (d) {
                                return d.id || (d.id = ++idex);
                            }),
                        /*etapesGroupe1 = etapesSvg
                        	.enter()
                        	.append("svg")
                        	.attr("id",function(d){return "ii"})    	    		
                        	.attr("width",20)
                         */
                        zoomEtape=d3.zoom()
                            .scaleExtent([1,1])
                            .on("zoom",function() {
                                //on cache le tooltip (si besoin)
                                d3.select("#tooltip").transition().duration(100).style("opacity", 0);
                                //on assigne le transform à l'étape correspondante (seulement en y) 
                                etapesGroupeEnter.select("#etape_"+this.getAttribute("id"))
                                    .attr("transform",d=>"translate(0,"+d3.event.transform.y+")")})                            
                        etapesGroupeEnter = etapesSvg.enter()
                            .append("svg").attr("class", "etape")
                            .attr("width",function(d){
                                indice=ticks.invert(d.time)
                                return x(indice+1)-x(indice)-15 //10 à gauche, 5 à droite
                            }).attr("height","100%").attr("transform",d=>"translate("+(x(ticks.invert(d.time)) + 10)+")")
                        etapesGroupe=etapesGroupeEnter
                            .append("g")
                            .attr("id",d=>"etape_"+d.id);
                   //ajout du rectangle de zoom 
                    etapesGroupeEnter.append("rect")
                        .attr("class","zoomNS")
                        .attr("id",d=>d.id) //pour retourver l'étape g correspondante  
                        .attr("width","100%")
                        .attr("height","100%")
                        .style("opacity",0.2)
                        .style("fill","red")
                        .call(tooltip,"Click pour pan <br/>Double click pour RAZ",2000)
                        .call(zoomEtape)
                        .on("dblclick.zoom",function(){
                            etapesGroupeEnter.select("#etape_"+this.getAttribute("id"))
                                .attr("transform",d=>"translate(0,0)")
                        })
                       
                        
                            
                            
                        
                    /*
                    définition des gradients
                     */
                    var gradientPair = scriptSvg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "gradientPair").attr("gradientUnits",
                        "userSpaceOnUse");
                    gradientPair.append("stop").attr("offset", "0")
                        .attr("stop-color", "green").attr(
                            "stop-opacity", "0.5");
                    gradientPair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");

                    var gradientImpair = scriptSvg.append(
                        "linearGradient").attr("y1", 0).attr("y2",
                        0).attr("x1", "0").attr("x2", "50").attr(
                        "id", "gradientImpair").attr(
                        "gradientUnits", "userSpaceOnUse");
                    gradientImpair.append("stop").attr("offset", "0")
                        .attr("stop-color", "blue").attr(
                            "stop-opacity", "0.5");
                    gradientImpair.append("stop").attr("offset", "1")
                        .attr("stop-opacity", "0");

                    etapesGroupe.append("text").attr("class",
                        "timeetape").text(function (d) {
                        return "(" + d.id + ")" + d.time
                    }).attr("dy", sizeHeight - 1)
                    etapesGroupe.each(function (d, i) {
                        var coms = d3.select(this).selectAll(
                                '.groupeetape').data(d.commandes)
                            .enter().append("g")

                            .attr("class", "groupeetape");
                        coms.append("rect").attr(
                                "class",
                                function (d) {
                                    return ((d.index % 2 == 0) ? "pair" :
                                        "impair");
                                }).attr(
                                "y",
                                function (d, j) {
                                    return j * sizeHeight + d.index *
                                        (sizeHeight / 2) +
                                        decalageFirst
                                }).attr("x", function (d) {
                                return d.niveau * decalageNiveau
                            }).attr("width", 50).attr("height", sizeHeight)
                            .attr("fill", "url(#gradient)");
                        coms.append('text').attr("class", "textetape ")
                            .attr(
                                "dy",
                                function (d, j) {
                                    return (j + 1) * sizeHeight +
                                        d.index *
                                        (sizeHeight / 2) +
                                        decalageFirst
                                }).attr("dx", function (d) {
                                return d.niveau * decalageNiveau
                            }).text(function (e, j) {
                                return e.commande
                            })
                    })
                    /*
                    scriptSvg
                        .selectAll(".etape")
                        .attr(
                            "transform",
                            function (d) {
                                return "translate(" +
                                    (x(ticks
                                        .invert(d.time)) + 10) +
                                    ",0)"
                            })
*/
                    etapesSvg.selectAll(".etape").exit().remove()
                })
    }
}
function setActions(actions) {
    //constrruit les lignes d'actions et les details
    actionNode = actionSvg.selectAll(".actionLine")
        .data(actions, d=>d.d3id);
    actionNode
        .enter()
        .append("line")
        .attr("class", d=>"actionLine " + d.evenement.type)
        .attr("x1",d=> x2(ticks.invert(d.evenement.time)))
        .attr("x2",d=>x2(ticks.invert(d.evenement.time)))
        .attr("y1", 0)
        .attr("y2", actionSvg.attr("height"))
        .call(function (d) {
            tooltip(d, d.datum().evenement.type_display +
                "<br/>" +
                d.datum().type_display +
                "<br/>" +
                d.datum().evenement.time +
                "(" +
                ticks
                .invert(d.datum().evenement.time)
            )
        });

    actionNode.exit().remove();
    //actions dans affichage
    affichageActionNode = ligneActionSvg
        .selectAll(".actionNode")
        .data(actions, d=> d.d3id);
    affichageActionNodeEnter = affichageActionNode
        .enter()
        .append("g").attr("class", "actionNode");
    affichageActionNodeEnter
        .append("line")
        .attr("class",d=> "actionLine " + d.evenement.type)
        .attr("x1", d=> x(ticks.invert(d.evenement.time)))
        .attr("x2", d=> x(ticks.invert(d.evenement.time)))
        .attr("y1", 0)
        .attr("y2",affichageSvg.attr("height"));

    affichageActionNode.exit().remove();
    //construction des détails (rectabnlge et texte)
    detail = ligneActionSvg
        .selectAll(".detail")
        .data(actions, d=>d.d3id);
    detailEnter = affichageActionNodeEnter
        .append("g")
        .attr("class", "detail")
        .attr("id", d=>"detail_" + d.id)
        .call(function (d) {
            tooltip(d, d.datum().evenement.type_display +
                "<br/>" +
                d.datum().type_display +
                "<br/>" +
                d.datum().evenement.time
            )
        });
    detailEnter
        .append("rect")
        .attr("class", d=> "actionrect " + d.evenement.type)
        .attr("width", 100)
        .attr("height", 20)
        .attr("fill", "brown")
    detailEnter
        .append("text")
        .text(d=> d.type_display)
        .attr("dy", 10)
        .attr("dx", 5)
    //placemeent
    detailEnter
        .attr("transform", d=> "translate(" +
                                x(ticks.invert(d.evenement.time)) +
                                "," + affichageSvg.attr("height") +
                                ") rotate(-90)"
        );
    detail.exit().remove();
}

function updateAffichageActions() {
    if (affichageActionNode) {
        console.log('sel', affichageSvg.selectAll(".actionLine"))
        affichageSvg.selectAll(".actionLine")
            .attr("x1", function (d) {
                console.log('cakc');
                return x(ticks.invert(d.evenement.time))
            }).attr("x2", function (d) {
                return x(ticks.invert(d.evenement.time))
            }).attr("y1", 0).attr("y2", affichageSvg.attr("height")).on(
                "mouseover",
                function (d) {
                    divTooltip.transition().duration(200).style("opacity", .9);
                    divTooltip.html(
                        d.evenement.type_display + "<br/>" + d.type_display +
                        "A<br/>" + d.evenement.time).style(
                        "left", (d3.event.pageX) + "px").style("top",
                        (d3.event.pageY - 28) + "px");
                })

        affichageSvg.selectAll(".detail").attr(
            "transform",
            function (d) {
                return "translate(" + x(ticks.invert(d.evenement.time)) +
                    "," + affichageSvg.attr("height") +
                    ") rotate(-90)"
            })       
        scriptSvg.selectAll(".etape") .attr("width",function(d){
                                indice=ticks.invert(d.time)
                                return x(indice+1)-x(indice)-15 //10 à gauche, 5 à droite
                            }).attr("height","100%").attr("transform",d=>"translate("+(x(ticks.invert(d.time)) + 10)+")")
        
    }
}

function brushed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "zoom")
        return; // ignore brush-by-zoom
    var s = d3.event.selection || x2.range();
    x.domain(s.map(x2.invert, x2));
    //focus.select(".area").attr("d", area);   
    affichageSvg.select(".axis--x").call(xAxis);
    affichageSvg.select(".zoom").call(zoom.transform,
        d3.zoomIdentity.scale(width / (s[1] - s[0])).translate(-s[0], 0));
    updateAffichageActions()
}

function zoomed() {
    if (d3.event.sourceEvent && d3.event.sourceEvent.type === "brush")
        return; // ignore zoom-by-brush
    var t = d3.event.transform;
    x.domain(t.rescaleX(x2).domain());
    //focus.select(".area").attr("d", area);    
    affichageSvg.select(".axis--x").call(xAxis);
    actionSvg.select(".brush").call(brush.move, x.range().map(t.invertX, t));
    updateAffichageActions()
}