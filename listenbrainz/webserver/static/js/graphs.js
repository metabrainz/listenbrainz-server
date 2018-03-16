/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2017 MetaBrainz Foundation Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

function draw_artist_graph(data) {

    var svg = d3.select("#graph").append("svg")
                                 .attr("height", (40 * data.length).toString())
                                 .attr("width", "100%");
    svg.selectAll(".row")
       .data(data)
       .enter().append("rect")
               .attr("class", "row")
               .attr("height", "40")
               .attr("width", "100%")
               .attr("x", "0")
               .attr("y", function(d, i) { return 40 * i; })
               .attr("fill", function(d, i) { return i % 2 == 0 ? "#F9F9F9" : "#FFFFFF"; })

    svg.selectAll(".bar")
       .data(data)
       .enter().append("rect")
               .attr("class", "bar")
               .attr("height", "30")
               .attr("width", function(d, i) {return Math.max(((d.listen_count * 50) / data[0].listen_count), 10).toString() + "%";})
               .attr("x", "50%")
               .attr("y", function(d, i) { return 40 * i + 5; });

    svg.selectAll(".index")
       .data(data)
       .enter().append("text")
               .text(function(d, i) { return (i + 1).toString(); })
               .attr("class", "index")
               .attr("x", "1%")
               .attr("y", function(d, i) { return 40 * i + 25; });

    svg.selectAll(".artist-names")
       .data(data)
       .enter().append("text")
               .text(function(d, i) { return d.artist_name; })
               .attr("class", "artist-names")
               .attr("x", "7%")
               .attr("y", function(d, i) { return 40 * i + 25; });

    svg.selectAll(".listen-counts")
       .data(data)
       .enter().append("text")
               .text(function(d, i) { return d.listen_count })
               .attr("class", "listen-counts")
               .attr("x", "50.5%")
               .attr("y", function(d, i) {return 40 * i + 25; });
}
