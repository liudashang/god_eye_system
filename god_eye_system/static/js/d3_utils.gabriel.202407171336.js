function topology_icon_generate(node, rectHeight, rectWidth, updateFlag = false) {



    $.get("/topology/node_type_list",
        function (data, textStatus, jqXHR) {
            data.forEach(el => {
                var icon_offset = 50;
                var icon_scale = 1;
                if (el.name == "PC") {
                    icon_scale = 0.7;
                }
                node.filter(d => { return d.node_type == el.name })
                    .append("image")
                    .attr("href", el.img_url)
                    .attr("x", -(rectWidth / 4))
                    .attr("y", 0)
                    .attr("width", rectWidth)
                    .attr("height", rectHeight)
                    .attr("transform", d => `translate(${(rectWidth - icon_offset) / 2},1)scale(${icon_scale})`)
            })

            if (updateFlag) {
                simulation.alpha(1).restart().tick();
            }
        },
        "json"
    );
}

function topology_icon_update(node, id, node_type, updateFlag = false, appendFlag = false) {

    $.get("/topology/node_type_list",
        function (data, textStatus, jqXHR) {
            data.forEach(el => {
                if (el.name != node_type) {
                    return;
                }

                if (appendFlag) {
                    var icon_offset = 50;
                    var icon_scale = 1;
                    if (el.name == "PC") {
                        icon_scale = 0.7;
                    }
                    node.filter(d => { return d.id == id })
                        .append("image")
                        .attr("href", el.img_url)
                        .attr("x", -(rectWidth / 4))
                        .attr("y", 0)
                        .attr("width", rectWidth)
                        .attr("height", rectHeight)
                        .attr("transform", d => `translate(${(rectWidth - icon_offset) / 2},1)scale(${icon_scale})`)
                } else {
                    node.filter(d => { return d.id == id })
                        .select("image")
                        .attr("href", el.img_url);
                }
            })

            if (updateFlag) {
                simulation.alpha(1).restart().tick();
            }
        },
        "json"
    );
}

function group_x_position(group, i) {
    var minX;

    //first
    minX = group.nodes[0].x;
    //every
    group.nodes.forEach(target => {
        if (target.x < minX) {
            minX = target.x;
        }
    });
    group.x = minX - i;
    return group.x;
}
function group_width(group, i, rectWidth) {
    var minX;
    var maxX;

    //first
    minX = group.nodes[0].x;
    maxX = group.nodes[0].x;
    //every
    group.nodes.forEach(target => {
        if (target.x < minX) {
            minX = target.x;
        }
        if (target.x > maxX) {
            maxX = target.x;
        }

    });
    group.width = maxX - minX + rectWidth + 2 * i;
    return group.width;
}
function group_y_position(group, i) {
    var minY;

    //first
    minY = group.nodes[0].y;
    //every
    group.nodes.forEach(target => {
        if (target.y < minY) {
            minY = target.y;
        }
    });
    group.y = minY - i;
    return group.y;
}
function group_height(group, i, rectHeight) {
    var minY;
    var maxY;

    //first

    minY = group.nodes[0].y;
    maxY = group.nodes[0].y;
    //every
    group.nodes.forEach(target => {
        if (target.y < minY) {
            minY = target.y;
        }
        if (target.y > maxY) {
            maxY = target.y;
        }
    });
    group.height = maxY - minY + rectHeight + 2 * i;
    return group.height;
}

function change_brush_mode(simulation, topology_name) {
    if (need_make_link) {
        toastr.warning("请关闭画线模式！");
        return false;
    }
    if (mode == "zoom") {
        $("#biaoti").append('<span class="badge badge-info" id="kuaijiebujumoshi">快捷布局模式</span>');
        toastr.success("开启快捷布局模式");
        svg_contextmenu(undefined,"（点击关闭）");
        $("#brushMode").html('<i class="fa fa-stop" aria-hidden="true"></i>快捷布局');
        mode = "brush";
        simulation.gabriel_svg.on(".zoom", null);
        init_brush();
    } else if (mode == "brush") {
        if (simulation.gabriel_brush != undefined) {
            simulation.gabriel_svg_g.call(
                simulation.gabriel_brush.clear
            );
            simulation.gabriel_svg_g.call(
                simulation.gabriel_brush.extent([[0, 0], [0, 0]])
            );
        }
        simulation.gabriel_svg_g.on(".brush", null);
        $("#biaoti #kuaijiebujumoshi").remove();
        toastr.success("关闭快捷布局模式");
        svg_contextmenu();
        $("#brushMode").html('<i class="fa fa-play" aria-hidden="true"></i>快捷布局');
        mode = "zoom";
        init_zoom();
    }
}

function make_a_link(simulation, topology_name) {
    if (mode == "brush") {
        toastr.warning("请关闭快捷布局模式！");
        return false;
    }
    if (need_make_link) {
        line_contextmenu();
        svg_contextmenu();
        $("#biaoti #huaxianmoshi").remove();
        toastr.success("关闭划线模式");
        d3.select("div.top svg").remove();
        get_data();
        $("#makeALink").html('<i class="fa fa-play" aria-hidden="true"></i>画连接线');
        need_make_link = false;
    } else {
        $("#biaoti").append('<span class="badge badge-info" id="huaxianmoshi">画线模式——依次单击【节点】连线；双击【连线】删除！</span>');
        line_contextmenu(true);
        //bindLinkClickEvent_Remove(simulation);
        svg_contextmenu('（点击关闭）');

        d3.select("div.top svg")
            .selectAll("g.node")
            .on("click", (e, d) => {
                if (make_link_list.length == 0) {
                    make_link_list.push(d.id);

                    d3.select("div.top svg").selectAll("g.node")
                        .filter((d, i) => d.id == make_link_list[0]).append("circle")
                        .attr("stroke", "white")
                        .attr("fill", d => "green")
                        .attr("fill-opacity", 0.5)
                        .attr("stroke-width", 1.5)
                        .attr("cx", d => rectWidth / 2)
                        .attr("cy", d => rectHeight / 2)
                        .attr("r", () => Math.max(rectWidth, rectHeight) / 2 + 1);
                } else {
                    make_link_list.push(d.id);

                    /* 判断两次单击是否是同一节点，是将删除圆圈清空待连接数组*/
                    if (make_link_list[0] == make_link_list[1]) {
                        d3.select("div.top svg").selectAll("g.node")
                            .filter((d, i) => {
                                if (make_link_list[0] == d.id) {
                                    start_node = { x: d.x, y: d.y };
                                    return true
                                }
                                if (make_link_list[1] == d.id) {
                                    end_node = { x: d.x, y: d.y };
                                    return true
                                }
                            }).select("circle").remove();
                        make_link_list = [];
                        return false;
                    }

                    d3.select("div.top svg").selectAll("g.node")
                        .filter((d, i) => d.id == make_link_list[1]).append("circle")
                        .attr("stroke", "white")
                        .attr("fill", d => "green")
                        .attr("fill-opacity", 0.5)
                        .attr("stroke-width", 1.5)
                        .attr("cx", d => rectWidth / 2)
                        .attr("cy", d => rectHeight / 2)
                        .attr("r", () => Math.max(rectWidth, rectHeight) / 2 + 1);

                    $.post("/topology/link_list", {
                        csrf_token: csrf_token,
                        topology_name: topology_name,
                        source: make_link_list[0],
                        target: make_link_list[1]
                    },
                        function (data, textStatus, jqXHR) {
                            let start_node, end_node;
                            toastr.success(data.info);
                            d3.select("div.top svg").selectAll("g.node")
                                .filter((d, i) => {
                                    if (make_link_list[0] == d.id) {
                                        start_node = { x: d.x, y: d.y };
                                        return true
                                    }
                                    if (make_link_list[1] == d.id) {
                                        end_node = { x: d.x, y: d.y };
                                        return true
                                    }
                                }).select("circle").remove();

                            //此处添加Link代码
                            add_link(simulation, make_link_list[0], make_link_list[1], data.id);
                            //bindLinkClickEvent_Remove(simulation);

                            make_link_list = [];
                        },
                        "json"
                    );
                }
            })
        toastr.success("开启画线模式");
        $("#makeALink").html('<i class="fa fa-stop" aria-hidden="true"></i>画连接线');
        need_make_link = true;

    }

}

function fix_all_position(simulation) {
    save_iframe_embed_style();
    data = [];
    simulation.gabriel_nodes.forEach(el => {
        data.push({ id: el.id, fx: el.x, fy: el.y });
    });
    $.post("/topology/fix_all_topology_position", {
        csrf_token: csrf_token,
        data: JSON.stringify(data)
    },
        function (data, textStatus, jqXHR) {
            toastr.success(data.info);
        },
        "json"
    );
}

function ticked() {

    let t_links = this.gabriel_links;
    let t_groups = this.gabriel_groups;
    let t_rectWidth = this.gabriel_rectWidth;
    let t_rectHeight = this.gabriel_rectHeight;
    let t_offset = this.gabriel_offset;

    this.gabriel_node.attr("transform", d => `translate(${d.x},${d.y})`);
    this.gabriel_link.select("path").attr('d', (d, i) => {
        return make_path(d, i, t_links, t_rectWidth, t_rectHeight);
    });

    this.gabriel_link.select("circle")
        .attr("fill", (d, i) => t_links[i].color)
        .select("animateMotion")
        .attr("path", (d, i) => {
            return make_circle_move_path(d, i, t_links, t_rectWidth, t_rectHeight);
        })
        .attr("dur", "30s")
        .attr("repeatCount", "indefinite");

    this.gabriel_link.select("text")
        .attr("fill", (d, i) => t_links[i].color)
        .attr("x", (d, i) => {
            let position = make_path(d, i, t_links, t_rectWidth, t_rectHeight, need_tooltip_position = true);
            return position[0]
        })
        .attr("y", (d, i) => {
            let position = make_path(d, i, t_links, t_rectWidth, t_rectHeight, need_tooltip_position = true);
            return position[1]
        })

    let fuyu = 20;

    this.gabriel_group.attr("transform", (d, i) => {
        let x = group_x_position(t_groups[i], fuyu);
        let y = group_y_position(t_groups[i], fuyu);
        return `translate(${x},${y})`;
    });
    this.gabriel_group.select("rect")
        .attr("width", (d, i) => group_width(t_groups[i], fuyu, t_rectWidth))
        .attr("height", (d, i) => group_height(t_groups[i], fuyu, t_rectHeight));
}

function generate_path(source, target, t_rectHeight, t_rectWidth, path_type) {
    let path_list = ['PC', 'JieRuSwitch', 'XianChangSwitch'];
    let flag = false;
    if (path_type == 0) {
        if (path_list.indexOf(source.node_type) == -1 && path_list.indexOf(target.node_type) == -1) {
            flag = true;
        }
    } else if (path_type == 1) {
        flag = true;
    }

    let sx = source.x + t_rectWidth / 2;
    let sy = source.y + t_rectHeight / 2;
    let tx = target.x + t_rectWidth / 2;
    let ty = target.y + t_rectHeight / 2;
    /*if (sx > tx) {
        let tmpx = tx;
        tx = sx;
        sx = tmpx;

        let tmpy = ty;
        ty = sy;
        sy = tmpy;
    }*/
    let scx = sx;
    let scy = 0;

    if (sy > ty) {
        scy = ty + t_rectHeight * 1.5;
    } else if ((sy - ty) <= 10 && (sy - ty) >= -10) {
        scy = ty;
    } else {
        scy = ty - t_rectHeight * 1.5;

    }
    //scy = (ty + sy)/2;
    let stx = tx;
    let sty = scy;
    return [flag, sx, sy, tx, ty, scx, scy, stx, sty];
}

function make_path(d, i, t_links, t_rectWidth, t_rectHeight) {
    let [flag, sx, sy, tx, ty, scx, scy, stx, sty] = generate_path(t_links[i].source, t_links[i].target, t_rectHeight, t_rectWidth, t_links[i].path_type);
    if (flag) {
        return `M ${sx} ${sy} L ${tx} ${ty},${sx} ${sy}`;
    }
    return `M ${sx} ${sy} L ${scx} ${scy},${stx} ${sty},${tx} ${ty},${stx} ${sty},${scx} ${scy},${sx} ${sy}`;
}

function make_circle_move_path(d, i, t_links, t_rectWidth, t_rectHeight) {
    let [flag, sx, sy, tx, ty, scx, scy, stx, sty] = generate_path(t_links[i].source, t_links[i].target, t_rectHeight, t_rectWidth, t_links[i].path_type);
    /*if (t_links[i].source.x > t_links[i].target.x) {
        if (flag) {
            return `M ${tx} ${ty} L ${sx} ${sy}`;
        }
        return `M ${tx} ${ty} L${stx} ${sty},${scx} ${scy},${sx} ${sy}`;
    }*/
    if (flag) {
        return `M ${sx} ${sy} L ${tx} ${ty}`;
    }
    return `M ${sx} ${sy} L ${scx} ${scy},${stx} ${sty},${tx} ${ty}`;

}

function make_tooltip_position_by_path(d, simulation) {
    let [flag, sx, sy, tx, ty, scx, scy, stx, sty] = generate_path(d.source, d.target, simulation.gabriel_rectHeight, simulation.gabriel_rectWidth, d.path_type);
    if (flag) {
        return [(sx + tx) / 2, (sy + ty) / 2];
    }
    return [(scx + stx) / 2, scy];
}


function svg_minus(factor = 0.01) {
    let value = $("#svg_minus_or_plus").val();
    let scale = value / 100 - factor;
    if (scale < 0.1) {
        scale = 0.1;
    }
    console.log(scale)
    scale_svg(scale)
}

function svg_plus(factor = 0.01) {
    let value = $("#svg_minus_or_plus").val();
    let scale = value / 100 + factor;
    if (scale > 1) {
        scale = 1;
    }
    scale_svg(scale)

}

function scale_svg(scale) {
    $("#svg_minus_or_plus").val(scale * 100);
    let transform = d3.zoomTransform(d3.select('g.all').node());
    transform.k = scale;
    transform.x = 0;
    transform.y = 0;
    d3.select("g.all")
        .attr("transform", transform);
    update_brush_size();
}

function myDelta(e) {
    return -e.deltaY * (e.deltaMode ? 120 : 1) / 3000;
}

function drag(simulation) {

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
        simulation.gabriel_tooltip.hide();
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;

        /*svg面积自适应*/
        if (d.fx + 100 > $("div.top").eq(0).width()) {
            $("div.top").eq(0).width(d.fx + 400)
            $("body").width(d.fx + 400)
            update_brush_size();
        }
        if (d.fy + 100 > $("div.top").eq(0).height()) {
            $("div.top").eq(0).height(d.fy + 300)
            update_brush_size();
        }


        simulation.gabriel_tooltip.hide();
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);

        let wangge_r = duiqi_wangge(simulation, d.fx, d.fy);
        d.x = wangge_r.x;
        d.y = wangge_r.y;

        d.fx = null;
        d.fy = null;
        simulation.gabriel_tooltip.hide();
    }

    return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
}

function duiqi_wangge(simulation, x, y) {
    //新增，对其网格
    let unit_height = simulation.gabriel_rectHeight + 20 * 2;
    let unit_width = simulation.gabriel_rectWidth + 10 * 2;
    let x_n = Math.floor(x / unit_width);
    let y_n = Math.floor(y / unit_height);

    if ((x % unit_width) / unit_width > 0.8) x_n = x_n + 1;
    if ((y % unit_height) / unit_height > 0.8) y_n = y_n + 1;


    let new_x = x_n * unit_width;
    let new_y = y_n * unit_height;
    return { x: new_x, y: new_y, unit: { x: unit_width, y: unit_height } }
}

function circleOnLink(simulation) {
    d3.interval(function () {
        simulation.gabriel_link.select("circle")
            .attr("fill", (d, i) => simulation.gabriel_links[i].color)
            .attr("cx", (d, i) => {
                d = { source: simulation.gabriel_links[i].source, target: simulation.gabriel_links[i].target };
                return (d.source.x + d.target.x + simulation.gabriel_rectWidth) / 2 + (d.target.x - d.source.x) * simulation.gabriel_offset
            })
            .attr("cy", (d, i) => {
                d = { source: simulation.gabriel_links[i].source, target: simulation.gabriel_links[i].target };
                return (d.source.y + d.target.y + simulation.gabriel_rectHeight) / 2 + (d.target.y - d.source.y) * simulation.gabriel_offset
            })

        simulation.gabriel_offset += 0.05;
        if (simulation.gabriel_offset >= 0.5) {
            simulation.gabriel_offset = -0.5;
        }
    }, 500);
}

function queryAlert(simulation, modalTitle, modalBody, modalID) {


    query_alert(simulation, modalTitle, modalBody, modalID);
    d3.interval(function () { query_alert(simulation, modalTitle, modalBody, modalID) }, 20000);
}

function getSuggestion(data) {
    new Promise((resolve, reject) => {
        let params = [];
        data.forEach(el => {
            if (el.type == 'node') {
                el.alert.forEach(alert_string => {
                    let alert = alert_string.split("--");
                    let result;
                    if (el.node_type == "Farm") {
                        result = alert[1];
                    } else {
                        result = alert[0];
                    }
                    params.push({
                        node_type: el.node_type,
                        node_id: el.node_id,
                        node_name: el.node_name,
                        alert: result
                    })
                });
            } else {
                params.push({
                    node_type: el.node_type,
                    node_id: el.node_id,
                    node_name: el.node_name,
                    alert: el.alert
                })
            }
        });

        $.post("/topology/get_alert_suggestions", {
            data: JSON.stringify(params)
        },
            function (data, textStatus, jqXHR) {

                if (data.results.length > 0) { //增加判断条件，返回结果为空时不显示建议按钮
                    $("#get_suggestions").removeClass('d-none');
                    let html_string_new = [];
                    data.results.forEach(el => {
                        html_string_new.push(`<p>${el.node_info}【${el.name}】——可能的原因：${el.reason},建议：${el.suggestion}<p>`);
                    })
                    $('#get_suggestions').popover({
                        title: '告警处理建议',
                        container: 'body',
                        content: html_string_new.join(''),
                        html: true,
                    })
                }
            },
            "json"
        );
    })
}

function query_alert(simulation, modalTitle, modalBody, modalID) {
    //toastr.error("测试","测试",{timeOut: 20000, onclick:toastr_onclick});
    $.get("/topology/moni_alert", { topology_name: simulation.gabriel_topology_name }, data => {
        //toastr.clear();

        let need_suggestion_alerts = []
        simulation.gabriel_nodes.forEach(el => {
            if (data.node_alerts[el.id] != undefined) {
                el.color = data.node_alerts[el.id].color;
                el.alert = data.node_alerts[el.id].alert;
                el.alert_count = data.node_alerts[el.id].alert_count;

                //获取告警建议而进行的数据整理
                let need_suggestion_alert = {
                    alert: el.alert,
                    node_type: el.node_type,
                    node_id: el.id,
                    node_name: el.name,
                    type: "node"
                }
                need_suggestion_alerts.push(need_suggestion_alert);

                if (el.alert[0] != "正常" && el.alert[0] != "未知") {
                    let alert_body = el.alert.join('<br>')
                    alert_body = `存在${data.node_alerts[el.id].alert_count}个问题<br>${alert_body}`
                    toastr.error(alert_body, `<span id="node-${el.id}">${el.name}</span>`, { timeOut: 10000, onclick: function (e) { toastr_onclick(e, simulation, modalTitle, modalBody, modalID) } });
                }
            } else {
                el.color = "transparent";
                el.alert_count = 0;
                el.alert = ['正常'];
            }
        });
        let warning_link_count = 0;
        let links_warning_list = [];
        simulation.gabriel_links.forEach(el => {
            if (data.link_alerts[el.id] != undefined) {
                el.color = data.link_alerts[el.id].color;
                el.alert = data.link_alerts[el.id].alert;

                //获取告警建议而进行的数据整理
                let need_suggestion_alert = {
                    alert: el.alert,
                    node_type: el.target.node_type,
                    node_id: el.target.id,
                    node_name: `至${el.target.name}线路`,
                    type: "link"
                }
                need_suggestion_alerts.push(need_suggestion_alert);

                if (el.alert != "正常" && el.alert != "未知") {
                    warning_link_count++;
                    links_warning_list.push(`<li><a href="javascript:link_alerts_list_show_modal(${el.id})">${el.source.name}->${el.target.name}</a> ${el.alert}</li>`)
                    //toastr.error(el.alert, `<span id="link-${el.id}">${el.source.name}->${el.target.name}</span>`, { onclick: function (e) { toastr_onclick(e, simulation, modalTitle, modalBody, modalID) } });
                }
            } else {
                el.color = "green";
                el.alert = "正常";
            }
        });

        if (warning_link_count > 0) {
            toastr.error(`当前存在${warning_link_count}处线路告警。`, `线路告警`, {
                onclick: function (e) {
                    $("#zabbixTitle").text("告警明细");
                    $("#modal_body_1").html(`<ul>${links_warning_list.join("")}</ul>`);
                    $("#modelId").modal('show');
                }
            });
        }

        //异步发起告警建议查询：
        if (need_suggestion_alerts.length > 0) {
            getSuggestion(need_suggestion_alerts);
        } else {
            //$('.alert').alert('close');
            $("#get_suggestions").addClass('d-none');
            $("#get_suggestions").popover('hide');
        }

        simulation.gabriel_svg_g.selectAll("g.node")
            .data(simulation.gabriel_nodes, function (d) { return d.id; }).select("rect").attr("fill", d => d.color ? d.color : "steelblue");

        simulation.gabriel_svg_g.selectAll("g.line_node")
            .data(simulation.gabriel_links, function (d) { return d.id; })
            .select("path")
            .attr("stroke", d => d.color);
        simulation.gabriel_svg_g.selectAll("g.line_node")
            .data(simulation.gabriel_links, function (d) { return d.id; })
            .select("circle")
            .attr("fill", d => d.color);
    });


    /*
    link.select("text")
        .attr("fill", d => d.color)
    */
}

function toastr_onclick(e, simulation, modalTitle, modalBody, modalID) {

    var alert_id = "";
    var alert_id_type = "";
    var alert_string = ""
    if ($(e.target).hasClass("toast-title")) {
        alert_string = $(e.target).children().filter("span").eq(0).attr("id");
    } else {
        alert_string = $(e.target).siblings().filter(".toast-title").eq(0).children().filter("span").eq(0).attr("id");
    }
    if (alert_string == undefined) {
        return false;
    }

    var alert_array = alert_string.split("-")
    alert_id_type = alert_array[0];
    alert_id = alert_array[1];

    if (alert_id_type == "node") {
        var d = simulation.gabriel_nodes.filter(el => { return el.id == alert_id }).shift();
        if (need_ip == 'yes') {
            $(modalTitle).text(`设备信息——${d.name}【${d.ip}】`)
        } else {
            $(modalTitle).text(`设备信息——${d.name}`)
        }
        $(modalBody).empty();
        $(modalID).modal('show');
        var start_time = moment().subtract(30, 'minutes').format('x');
        var end_time = moment().format('x');

        $.get("/topology/show_modal", {
            id: d.id,
            from: start_time,
            to: end_time
        }, function (data) {
            if (data == "未配置任何监控项") {
                toastr.info(data);
                return false;
            }
            $(modalBody).html(data);
            $(".metric_collapse").eq(0).collapse('show');
        });

    } else {
        var d = simulation.gabriel_links.filter(el => { return el.id == alert_id }).shift();
        $(modalTitle).text(`链路信息——${d.source.name}->${d.target.name}`)
        $(modalBody).empty();
        $(modalID).modal('show');
        var start_time = moment().subtract(30, 'minutes').format('x');
        var end_time = moment().format('x');
        $.get("/topology/show_modal", {
            id: d.id,
            from: start_time,
            to: end_time,
            metric_type: 1
        }, function (data) {
            if (data == "未配置任何监控项") {
                toastr.info(data);
                return false;
            }
            $(modalBody).html(data);
            $(".metric_collapse").eq(0).collapse('show');
        });

    }
}

function link_alerts_list_show_modal(alert_id) {
    let modalTitle = "#zabbixTitle";
    let modalBody = "#modal_body_1";
    let modalID = "#modelId";
    var d = simulation.gabriel_links.filter(el => { return el.id == alert_id }).shift();
    $(modalTitle).text(`链路信息——${d.source.name}->${d.target.name}`)
    $(modalBody).empty();
    $(modalID).modal('show');
    var start_time = moment().subtract(30, 'minutes').format('x');
    var end_time = moment().format('x');
    $.get("/topology/show_modal", {
        id: d.id,
        from: start_time,
        to: end_time,
        metric_type: 1
    }, function (data) {
        if (data == "未配置任何监控项") {
            toastr.info(data);
            return false;
        }
        $(modalBody).html(data);
        $(".metric_collapse").eq(0).collapse('show');
    });
}

function get_g_all_location() {
    let transform = d3.zoomTransform(d3.select('g.all').node());

    return transform;
}

function show_tooltip(d, simulation) {
    let offset = get_g_all_location();
    let scale = d3.zoomTransform(d3.select('g.all').node()).k;
    var i = 2,
        x = d.x + simulation.gabriel_rectWidth,
        y = d.y + simulation.gabriel_rectHeight / 2,
        dWidth = $("div.top").width(),
        dHeight = $("div.top").height();
    if (d.x + simulation.gabriel_rectWidth + 150 > dWidth && y * scale - 100 >= 0) {
        i = 3;
        x = d.x;
        y = d.y + simulation.gabriel_rectHeight / 2;
    }
    else if (y * scale - 100 < 0) {
        i = 1;
        x = d.x + simulation.gabriel_rectWidth / 2,
            y = d.y + simulation.gabriel_rectHeight;
    }
    var direction = ['bottom', 'top', 'left', 'right'];

    var rows = [
        {
            left: "序号",
            right: "{id}"
        },
        {
            left: "名称",
            right: "{name}"
        }
    ];
    var alert_array = d.alert;
    if (d.alert_count == 0) {
        rows.push({
            left: "状态信息",
            right: alert_array[0]
        });
    } else {
        rows.push({
            left: "状态信息",
            right: "存在" + d.alert_count + "个问题"
        });
        alert_array.forEach(el => {
            rows.push({
                left: "",
                right: el
            });
        });
    }
    rows.push({
        left: "*提示:点击查看监控项",
        right: ""
    });

    simulation.gabriel_tooltip
        .direction(direction[i])
        .content(rows)
        .tooltipFill("#F0F0F0")
        .x(x * scale + offset.x)
        .y(y * scale + offset.y)
        .show({ id: d.id, name: d.name, alert: d.alert })
}

function show_link_tooltip(d, simulation) {
    let offset = get_g_all_location();
    let scale = d3.zoomTransform(d3.select('g.all').node()).k;
    let position = make_tooltip_position_by_path(d, simulation);
    var i = 0,
        x = position[0],
        y = position[1];
    if (y * scale - 150 < 0) {
        i = 1;
    }

    var direction = ['bottom', 'top', 'left', 'right'];

    var rows = [
        {
            left: "序号",
            right: "{id}"
        },
        {
            left: "名称",
            right: "{name}"
        }
    ];
    var alert_array = d.alert.split("\n");
    if (alert_array.length == 1) {
        rows.push({
            left: "状态信息",
            right: d.alert
        });
    } else {
        rows.push({
            left: "状态信息",
            right: alert_array.shift()
        });
        alert_array.forEach(el => {
            rows.push({
                left: "",
                right: el
            });
        });
    }
    if (d.source_port !== null && d.target_port !== null) {
        rows.push({
            left: "端口",
            right: `${d.source_port} -> ${d.target_port}`
        });
    }
    if (d.alert != "未知") {
        rows.push({
            left: "*提示:点击查看监控项",
            right: ""
        });
    }

    simulation.gabriel_tooltip
        .direction(direction[i])
        .content(rows)
        .tooltipFill("#F0F0F0")
        .x(x * scale + offset.x)
        .y(y * scale + offset.y)
        .show({ id: d.id, name: d.source.name + '->' + d.target.name })
}

function bindToolTip(simulation) {
    simulation.gabriel_node.on('mouseenter', (e, d) => {
        show_tooltip(d, simulation);
        if (!need_make_link)
            strongNode(simulation, d.id, false);
    })
        .on('mouseleave', (e, d) => {
            simulation.gabriel_tooltip.hide();
            if (!need_make_link)
                strongNode(simulation, d.id);
        });

    simulation.gabriel_link.on('mouseenter', (e, d) => {
        show_link_tooltip(d, simulation);
        if (!need_make_link)
            strongLink(simulation, d, false);
    })
        .on('mouseleave', (e, d) => {
            simulation.gabriel_tooltip.hide();
            if (!need_make_link)
                strongLink(simulation, d);
        });
}

function strongNode(simulation, id, hideflag = true) {
    let width = 1.5;
    let color = "transparent";
    if (!hideflag) {
        width = 4;
        color = "#00BFFF";
    }
    simulation.gabriel_svg_g.selectAll("g.node")
        .data(simulation.gabriel_nodes, function (d) { return d.id; }).select("rect")
        .filter((d, i) => { return d.id == id })
        .attr("stroke-width", width)
        .attr("stroke", color);
}
function strongLink(simulation, link, hideFlag = true) {
    if (hideFlag) {
        let target_id = link.target.id;
        let source_id = link.source.id;
        simulation.gabriel_svg_g.selectAll("g.line_node")
            .data(simulation.gabriel_links, function (d) { return d.id; })
            .select("path")
            .filter((d, i) => { return d.id == link.id })
            .attr("stroke-opacity", 0.4)
            .attr("stroke-width", 3);
        //.attr("stroke", link.color);

        strongNode(simulation, target_id, hideFlag)
        strongNode(simulation, source_id, hideFlag)
    } else {
        let color = "blue";
        let target_id = link.target.id;
        let source_id = link.source.id;
        simulation.gabriel_svg_g.selectAll("g.line_node")
            .data(simulation.gabriel_links, function (d) { return d.id; })
            .select("path")
            .filter((d, i) => { return d.id == link.id })
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 8);
        //.attr("stroke", color);

        strongNode(simulation, target_id, hideFlag)
        strongNode(simulation, source_id, hideFlag)
    }
}

function bindClickEvent(simulation, modalTitle, modalBody, modalID) {
    bindNodeClickEvent(simulation, modalTitle, modalBody, modalID);
    bindLinkClickEvent(simulation, modalTitle, modalBody, modalID);
}

function bindLinkClickEvent(simulation, modalTitle, modalBody, modalID) {
    simulation.gabriel_link.on("click", (e, d) => {
        $(modalTitle).text(`链路信息——${d.source.name}->${d.target.name}`)
        $(modalBody).empty();
        $(modalID).modal('show');
        var start_time = simulation.gabriel_from;
        var end_time = simulation.gabriel_to;
        if (!simulation.gabriel_time_flag) {
            start_time = moment().subtract(3, 'hour').format('x');
            end_time = moment().format('x');
        }
        $.get("/topology/show_modal", {
            id: d.id,
            from: start_time,
            to: end_time,
            metric_type: 1
        }, function (data) {
            if (data == "未配置任何监控项") {
                toastr.info(data);
                return false;
            }
            $(modalBody).html(data);
            $(".metric_collapse").eq(0).collapse('show');
        });
    });
}

function bindLinkClickEvent_Remove(simulation) {
    simulation.gabriel_link.on("click", (e, d) => {
        return false;
    });
    simulation.gabriel_link.on("dblclick", (e, d) => {
        $.get("/topology/edit_link_info", {
            id: d.id
        },
            function (data, textStatus, jqXHR) {
                toastr.success(data.info);
                removeLink(simulation, d.id);
            },
            "json"
        );
    });
}

function bindNodeRightClickEvent(simulation) {
    simulation.gabriel_node.on("contextmenu", (e, d) => {
        if (d.node_type == 'PC' || d.node_type == "XianChangSwitch") {
            e.preventDefault();
            $("#modelId3_id").val(d.id);
            $("#modelId3_name").val(d.name);
            $("#modelId3_ip").val(d.ip);
            $("#modelId3_node_type").val(d.node_type);

            $("#modelId3_submit").removeClass("d-none");
            $("#modelId3_submit_add").addClass("d-none");
            $("#modelId3").modal('show');
        }
    });
}

function bindNodeClickEvent(simulation, modalTitle, modalBody, modalID) {
    simulation.gabriel_node.on("click", (e, d) => {
        if (need_ip == 'yes') {
            $(modalTitle).text(`设备信息——${d.name}【${d.ip}】`)
        } else {
            $(modalTitle).text(`设备信息——${d.name}`)
        }
        $(modalBody).empty();
        $(modalID).modal('show');
        var start_time = simulation.gabriel_from;
        var end_time = simulation.gabriel_to;
        if (!simulation.gabriel_time_flag) {
            start_time = moment().subtract(3, 'hour').format('x');
            end_time = moment().format('x');
        }
        $.get("/topology/show_modal", {
            id: d.id,
            from: start_time,
            to: end_time
        }, function (data) {
            if (data == "未配置任何监控项") {
                toastr.info(data);
                return false;
            }
            $(modalBody).html(data);
            $(".metric_collapse").eq(0).collapse('show');
        });
    });
}

function initGroup(simulation) {
    var group = simulation.gabriel_svg_g.selectAll("g.group")
        .data(simulation.gabriel_groups, function (d) { return d.id; })
        .enter()
        .append("g")
        .attr("class", "group")
        .attr("fill", "currentColor")
        .attr("stroke-linecap", "round")
        .attr("stroke-linejoin", "round");

    group.append("rect")
        .attr("rx", simulation.gabriel_rectWidth * 0.1)
        .attr("fill", d => d.color ? d.color : "yellow")
        .attr("stroke", "transparent")
        .attr("stroke-width", 1.5)
        .attr("fill-opacity", 0.7);

    group.append("text")
        .attr("class", "group-name")
        .attr("textLength", d => d.name.length * 12)
        .attr("lengthAdjust", "spacingAndGlyphs")
        .attr("x", 5)
        .attr("y", -5)
        .text(d => d.name);
    return group;
}

function initLink(simulation, update = false) {
    var link = simulation.gabriel_svg_g.selectAll("g.line_node")
        .data(simulation.gabriel_links, function (d) { return d.id; })
        .enter()
        .append("g")
        .attr("class", "line_node");

    link.append("path")
        .attr("stroke-width", 3)
        .attr("stroke-opacity", 0.4)
        .attr("stroke", d => d.color);

    link.append("circle")
        .attr("stroke", "white")
        .attr("fill", d => d.color)
        .attr("fill-opacity", 0.5)
        .attr("stroke-width", 1.5)
        .attr("r", 4)
        .append("animateMotion")
        .attr("path", `M 0 0 L 0 0`)
        .attr("dur", "30s")
        .attr("repeatCount", "indefinite");

    /*
    link.append("text")
        .text(d => d.speed);
    */
    if (update) {
        return simulation.gabriel_link.data(simulation.gabriel_links, function (d) { return d.id; }).merge(link);
    }
    return link;
}

function updateLink(simulation) {
    return initLink(simulation, true)
}

function removeLink(simulation, id) {
    simulation.gabriel_links = simulation.gabriel_links.filter(el => el.id != id);
    simulation.gabriel_link.data(simulation.gabriel_links, function (d) { return d.id; }).exit().remove();
    simulation.gabriel_link = simulation.gabriel_link.data(simulation.gabriel_links, function (d) { return d.id; });
    simulation.alpha(1).restart().tick();
}

function removeNode(simulation, id) {
    simulation.gabriel_nodes = simulation.gabriel_nodes.filter(el => el.id != id);
    simulation.gabriel_node.data(simulation.gabriel_nodes, function (d) { return d.id; }).exit().remove();
    simulation.gabriel_node = simulation.gabriel_node.data(simulation.gabriel_nodes, function (d) { return d.id; });
    waiting_del_list = [];
    simulation.gabriel_links.forEach(el => {
        if (el.source.id == id || el.target.id == id) {
            waiting_del_list.push(el.id);
        }
    })
    waiting_del_list.forEach(el => {
        removeLink(simulation, el);
    })
    simulation.alpha(1).restart().tick();
}

function initNode(simulation, update = false) {
    var node = simulation.gabriel_svg_g.selectAll("g.node")
        .data(simulation.gabriel_nodes, function (d) { return d.id; })
        .enter()
        .append("g")
        .attr("class", "node")
        .attr("fill", "currentColor")
        .attr("stroke-linecap", "round")
        .attr("stroke-linejoin", "round")
        .call(drag(simulation));

    node.append("rect")
        .attr("rx", simulation.gabriel_rectWidth * 0.1)
        .attr("fill", d => "transparent")
        .attr("stroke-width", 1.5)
        .attr("fill-opacity", 0.8)
        .attr("width", simulation.gabriel_rectWidth)
        .attr("height", simulation.gabriel_rectHeight);

    node.append("text")
        //.attr("textLength", d => d.name.length * 8)
        .attr("class", "node-name")
        .attr("textLength", d => {
            let length = d.name.length * 8;
            if (/.*[\u4e00-\u9fa5]+.*$/.test(d.name)) {
                length = d.name.length * 15;
            }
            if (simulation.gabriel_rectWidth > length) {
                return length
            } else {
                return simulation.gabriel_rectWidth - 5
            }
        })
        .attr("lengthAdjust", "spacingAndGlyphs")
        //.attr("x", (d, i, n) => { return (simulation.gabriel_rectWidth - 100) / 2 })
        .attr("y", -3)
        .text(d => d.name);

    if (need_ip == "yes") {
        node.append("text")
            //.attr("textLength", d => d.ip.length * 5)
            .attr("class", "node-ip")
            .attr("textLength", d => {
                if (simulation.gabriel_rectWidth > d.ip.length * 5) {
                    return d.ip.length * 5
                } else {
                    return simulation.gabriel_rectWidth - 5
                }
            })
            .attr("lengthAdjust", "spacingAndGlyphs")
            .attr("y", simulation.gabriel_rectHeight + 12)
            .text(d => d.ip);
    }

    if (update) {
        return simulation.gabriel_node.data(simulation.gabriel_nodes, function (d) { return d.id; }).merge(node);
    }
    return node;
}

function updateNode(simulation) {
    return initNode(simulation, true)
}

function change_node_text(simulation, node_id, new_name, new_ip, new_node_type) {
    let node = simulation.gabriel_node.filter(d => { return d.id == node_id });
    node.select("text.node-name").text(d => {
        d.name = new_name;
        d.node_type = new_node_type;
        d.ip = new_ip;
        return new_name
    });
    if (need_ip == "yes")
        node.select("text.node-ip").text(d => {
            return d.ip;
        });
    topology_icon_update(simulation.gabriel_node, node_id, new_node_type, true);
}

function brushed(e) {
    if (e.mode == undefined) return false;

    x0 = e.selection[0][0];
    y0 = e.selection[0][1];
    x1 = e.selection[1][0];
    y1 = e.selection[1][1];
    if (e.mode == "handle") {
        simulation.gabriel_brush_selections = [];
        simulation.gabriel_nodes.forEach(el => {
            if (x0 < el.x && el.x < x1 && y0 < el.y && el.y < y1) {
                simulation.gabriel_brush_selections.push({
                    id: el.id,
                    tx: el.x - x0,
                    ty: el.y - y0,
                });
            }
        });
    } else if (e.mode == "drag") {
        let had_duiqi = [];
        simulation.gabriel_brush_selections.forEach(el => {
            simulation.gabriel_nodes.forEach(node => {
                if (node.id == el.id) {
                    let wangge_r = duiqi_wangge(simulation, el.tx + x0, el.ty + y0);
                    let had_duiqi_el = `x:${wangge_r.x},y:${wangge_r.y}`;
                    if (had_duiqi.indexOf(had_duiqi_el) == -1) {
                        node.fx = wangge_r.x;
                        node.fy = wangge_r.y;

                    } else {
                        let new_x = wangge_r.x + wangge_r.unit.x;

                        had_duiqi_el = `x:${new_x},y:${wangge_r.y}`;
                        while (had_duiqi.indexOf(had_duiqi_el) != -1) {
                            new_x = new_x + wangge_r.unit.x;
                            had_duiqi_el = `x:${new_x},y:${wangge_r.y}`;
                        }
                        node.fx = new_x;
                        node.fy = wangge_r.y;
                    }
                    had_duiqi.push(had_duiqi_el);
                }
            })
        });
        simulation.alpha(1).restart().tick();
    }
}

function update_brush_size() {
    if (mode != "brush") return false;
    d3.select("g.all")
        .call(
            simulation.gabriel_brush.extent(() => {
                let transform = d3.zoomTransform(d3.select('g.all').node());
                return [[0, 0], [$("div.top").width() / transform.k, $("div.top").height() / transform.k]];
            })
        );
}

function init_zoom() {
    if (mode == "zoom") {
        d3.select("svg.svg-element").call(
            d3.zoom()
                .on("zoom", function (e) {
                    $("#svg_minus_or_plus").val(e.transform.k * 100);
                    d3.select("g.all")
                        .attr("transform", e.transform);
                })
                .wheelDelta((e) => {
                    return -e.deltaY * (e.deltaMode ? 120 : 1) / 2000;
                })
        )
    }
}

function init_brush() {
    if (mode == "brush") {
        simulation.gabriel_svg_g.call(
            simulation.gabriel_brush = d3.brush()
                .on("brush", brushed)
                .extent(() => {
                    let transform = d3.zoomTransform(d3.select('g.all').node());
                    return [[-transform.x / transform.k, -transform.y / transform.k], [$("div.top").width() / transform.k, $("div.top").height() / transform.k]];
                })
        );
    }
}

function setup_top(inNodes, inLinks, inGroups, rectHeight, rectWidth, from, to) {
    const collideForce = 35;
    var offset = -0.5;
    var brush;
    var svg = d3.select("div.top")
        .append("svg:svg")
        .attr("class", "svg-element");
    init_zoom();

    var svg_g = svg.append("g")
        .attr("class", "all");

    var tooltip = d3.componentsTooltip()
        .container('.svg-element');
    $("svg.tooltip-shadow-wrapper-svg").addClass("d-none");

    var nodes = inNodes.map(d => Object.create(d));

    var links = inLinks.map(d => Object.create(d));

    var groups = inGroups.map(d => Object.create(d));

    links.forEach(d => {
        let nodes1 = nodes.filter(el => { return el.id == d.source; });
        d.source = nodes1[0];

        nodes1 = nodes.filter(el => { return el.id == d.target; });
        d.target = nodes1[0];
    });

    groups.forEach(d => {
        for (var i = 0; i < d.nodes.length; i++) {
            nodes1 = nodes.filter(el => { return el.id == d.nodes[i] });
            d.nodes[i] = nodes1[0];
        }
    });

    var simulation = d3.forceSimulation(nodes)
        .force("charge", d3.forceCollide(collideForce))
        .on("tick", ticked);

    simulation.gabriel_time_flag = false;
    simulation.gabriel_rectWidth = rectWidth;
    simulation.gabriel_rectHeight = rectHeight;
    simulation.gabriel_from = from;
    simulation.gabriel_to = to;
    simulation.gabriel_offset = offset;
    simulation.gabriel_tooltip = tooltip;
    simulation.gabriel_topology_name = topology_name;

    simulation.gabriel_svg = svg;
    simulation.gabriel_svg_g = svg_g;
    simulation.gabriel_brush = brush;
    simulation.gabriel_nodes = nodes;
    simulation.gabriel_links = links;
    simulation.gabriel_groups = groups;
    simulation.gabriel_brush_selections = [];

    simulation.gabriel_group = initGroup(simulation);
    simulation.gabriel_link = initLink(simulation);
    simulation.gabriel_node = initNode(simulation);

    topology_icon_generate(simulation.gabriel_node, rectHeight, rectWidth);
    //circleOnLink(simulation);

    queryAlert(simulation, "#zabbixTitle", "#modal_body_1", "#modelId");

    bindToolTip(simulation);

    bindClickEvent(simulation, "#zabbixTitle", "#modal_body_1", "#modelId");

    //bindNodeRightClickEvent(simulation);

    return simulation;
}

function add_link(simulation, source_id, target_id, link_id, path_type = 0) {
    let data = { id: link_id, color: "green" };
    let nodes1 = simulation.gabriel_nodes.filter(el => { return el.id == source_id; });
    data.source = nodes1[0].id;

    let nodes2 = simulation.gabriel_nodes.filter(el => { return el.id == target_id; });
    data.target = nodes2[0].id;

    data = Object.create(data);
    data.source = nodes1[0];
    data.target = nodes2[0];
    data.path_type = path_type;

    simulation.gabriel_links.push(data);


    simulation.gabriel_link = updateLink(simulation);
    simulation.alpha(1).restart().tick();
    return true;
}

function add_node(simulation, new_id, new_name, new_ip, new_node_type, fx, fy) {
    let data = { id: new_id, name: new_name, ip: new_ip, node_type: new_node_type, fx: fx, fy: fy, x: fx, y: fy, alert: ["正常"], alert_count: 0 };

    data = Object.create(data);
    simulation.gabriel_nodes.push(data);

    simulation.gabriel_node = updateNode(simulation);
    simulation.nodes(simulation.gabriel_nodes);
    bindToolTip(simulation);
    topology_icon_update(simulation.gabriel_node, new_id, new_node_type, true, true);
    return true;
}


function save_iframe_embed_style() {
    let style_data = [];
    $(".draggable_resizable_iframe").each((i, el) => {
        style_data.push({
            id: $(el).attr("iframe_id"),
            height: $(el).outerHeight(true),
            width: $(el).outerWidth(true),
            top: $(el).offset().top,
            left: $(el).offset().left
        });
    });

    if (style_data.length > 0) {
        $.post("/topology/get_update_iframe_embed_url", {
            csrf_token: csrf_token,
            style: JSON.stringify(style_data)
        },
            function (data, textStatus, jqXHR) {
                if (data.error == 0) {
                    toastr.success(data.info);
                }
            },
            "json"
        );
    }
}

function svg_contextmenu(link_open = "（点击开启）", buju_open = "（点击开启）") {
    $.contextMenu('destroy', "svg.svg-element");
    if (node_edit_flag == "1") {
        let items = {
            makeLink: {
                name: "画连接线" + link_open,
                icon: "fa-pencil",
                callback: function (key, opt) {
                    make_a_link(simulation, topology_name);
                }
            },
            buju: {
                name: "快捷布局" + buju_open,
                icon: "fa-arrows",
                callback: function (key, opt) {
                    change_brush_mode(simulation, topology_name);
                }
            },
            split: {
                "type": "cm_separator"
            },
            guding: {
                name: "一键固定（保存节点位置）",
                icon: "fa-window-restore",
                callback: function (key, opt) {
                    fix_all_position(simulation);
                }
            },
            addNode: {
                name: "新增节点",
                icon: "fa-plus-square",
                callback: function (key, opt, event) {
                    $("#modelId3_hide_input_group").empty();
                    $("#modelId3_id").val("");
                    $("#modelId3_name").val("");
                    $("#modelId3_ip").val("");
                    $("#modelId3_node_type").val("");
                    $("#modelId3_topology_name").val(topology_name);

                    $("#modelId3_submit_add").removeClass("d-none");
                    $("#modelId3_submit").addClass("d-none");
                    $("#modelId3").modal('show');

                    let transform = d3.zoomTransform(d3.select('g.all').node());
                    let fx = (new_node_position.x - transform.x) / transform.k;
                    let fy = (new_node_position.y - $("svg.svg-element").offset().top - transform.y) / transform.k;

                    $("#modelId3_hide_input_group").html([
                        `<input type="hidden" name="fx" id="modelId3_fx" value="${fx}"> `,
                        `<input type="hidden" name="fy" id="modelId3_fy" value="${fy}">`,
                    ].join(''));

                }
            },
            configGroup: {
                name: "分组设置",
                icon: "fa-users",
                callback: function (key, opt, event) {
                    location.href = "/topology/node_group_config_page?topology_name=" + topology_name;
                }
            },
        };

        if (link_open == "（点击关闭）") {
            delete items.buju;
        }
        if (buju_open == "（点击关闭）") {
            delete items.makeLink;
        }

        $.contextMenu({
            // define which elements trigger this menu
            selector: "svg.svg-element",
            // define the elements of the menu
            items: items,
            build: function ($triggerElement, e) {
                new_node_position.x = e.originalEvent.x;
                new_node_position.y = e.originalEvent.y;
                return true;
            }
            // there's more, have a look at the demos and docs...
        });
    } else {
        $.contextMenu({
            // define which elements trigger this menu
            selector: "svg.svg-element",
            // define the elements of the menu
            items: {
                split: {
                    "type": "cm_separator"
                },
            }
            // there's more, have a look at the demos and docs...
        });
    }
}

function node_contextmenu(delFlag = false) {
    $.contextMenu('destroy', "g.node");
    if (delFlag) {
        $.contextMenu({
            // define which elements trigger this menu
            selector: "g.node",
            // define the elements of the menu
            items: {
                split: {
                    "type": "cm_separator"
                },
            }
            // there's more, have a look at the demos and docs...
        });
    } else {
        if (node_edit_flag == "1") {
            $.contextMenu({
                // define which elements trigger this menu
                selector: "g.node",
                // define the elements of the menu
                items: {
                    edit: {
                        name: "编辑",
                        icon: "fa-pencil-square-o",
                        callback: function (key, opt) {
                            $("#modelId3_hide_input_group").empty();
                            let d = d3.select(opt.$trigger[0]).datum();
                            $("#modelId3_id").val(d.id);
                            $("#modelId3_name").val(d.name);
                            $("#modelId3_ip").val(d.ip);
                            $("#modelId3_node_type").val(d.node_type);
                            $("#modelId3_topology_name").val(topology_name);

                            $("#modelId3_submit").removeClass("d-none");
                            $("#modelId3_submit_add").addClass("d-none");
                            $("#modelId3").modal('show');


                            console.log(simulation.gabriel_groups)
                        }
                    },
                    split: {
                        "type": "cm_separator"
                    },
                    remove: {
                        name: "删除",
                        icon: "fa-trash",
                        callback: function (key, opt) {
                            let d = d3.select(opt.$trigger[0]).datum();
                            $.get("/topology/edit_node_info", {
                                operation: 0,
                                id: d.id
                            }, data => {
                                if (data.error == 1) {
                                    toastr.warning(data.info);
                                } else {
                                    removeNode(simulation, d.id);
                                    toastr.success(data.info);
                                }
                            });
                        }
                    },
                }
                // there's more, have a look at the demos and docs...
            });
        }
    }
}

function line_contextmenu(delFlag = false) {
    $.contextMenu('destroy', "g.line_node");
    if (delFlag) {
        $.contextMenu({
            // define which elements trigger this menu
            selector: "g.line_node",
            // define the elements of the menu
            items: {
                remove: {
                    name: "删除",
                    icon: "fa-trash",
                    callback: function (key, opt) {
                        let d = d3.select(opt.$trigger[0]).datum();
                        $.get("/topology/edit_link_info", {
                            id: d.id
                        },
                            function (data, textStatus, jqXHR) {
                                toastr.success(data.info);
                                removeLink(simulation, d.id);
                            },
                            "json"
                        );
                    }
                },
                changeLinkType: {
                    name: "切换连线样式（直线、折线）",
                    icon: "fa-arrows-h",
                    callback: function (key, opt) {
                        let d = d3.select(opt.$trigger[0]).datum();
                        $.get("/topology/change_link_type", {
                            id: d.id
                        },
                            function (data, textStatus, jqXHR) {
                                toastr.success(data.info);
                                d.path_type = data.path_type;
                                removeLink(simulation, d.id);
                                add_link(simulation, d.source.id, d.target.id, d.id, d.path_type);
                            },
                            "json"
                        );
                    }
                }
            }
            // there's more, have a look at the demos and docs...
        });
    } else {
        if (node_edit_flag == "1") {
            $.contextMenu({
                // define which elements trigger this menu
                selector: "g.line_node",
                // define the elements of the menu
                items: {
                    split: {
                        "type": "cm_separator"
                    },
                }
                // there's more, have a look at the demos and docs...
            });
        }
    }
}