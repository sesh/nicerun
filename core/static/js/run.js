/*
    Utility Function
*/

function getWidth() {
  return Math.max(
    document.body.scrollWidth,
    document.documentElement.scrollWidth,
    document.body.offsetWidth,
    document.documentElement.offsetWidth,
    document.documentElement.clientWidth
  );
}

function zip(arrays) {
  return Array.apply(null, Array(arrays[0].length)).map(function (_, i) {
    return arrays.map(function (array) {
      return array[i];
    });
  });
}

function toHHMMSS(x) {
  var sec_num = parseInt(x, 10); // don't forget the second param
  var hours = Math.floor(sec_num / 3600);
  var minutes = Math.floor((sec_num - hours * 3600) / 60);
  var seconds = sec_num - hours * 3600 - minutes * 60;

  if (hours < 10) {
    hours = "0" + hours;
  }
  if (minutes < 10) {
    minutes = "0" + minutes;
  }
  if (seconds < 10) {
    seconds = "0" + seconds;
  }

  if (hours == "00") {
    if (minutes[0] == "0") {
      minutes = minutes[1];
    }
    return minutes + ":" + seconds;
  }

  if (hours[0] == "0") {
    hours = hours[1];
  }
  return hours + ":" + minutes + ":" + seconds;
}

/*
    Mapbox
*/

let map;
let mapCenter = [run.longitude_values[0], run.latitude_values[0]];
let mapZoom = 13;

function initMap() {
  console.log(MAP_STYLE);

  /* Map */
  let lon_lat_values = zip([run.longitude_values, run.latitude_values]);
  if (MAP_CROP) {
    crop = parseInt(MAP_CROP);
    lon_lat_values = lon_lat_values.slice(crop, lon_lat_values.length - crop);
  }

  const geojson = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "LineString",
          properties: {},
          coordinates: lon_lat_values,
        },
      },
    ],
  };

  mapboxgl.accessToken =
    "pk.eyJ1IjoiYnJudG4iLCJhIjoiY2lvNm9mZzk3MDJoN3ZibHpsYW5sbWw0cCJ9.Pwlwb-SGyANUls0K0R9kjg";

  map = new mapboxgl.Map({
    container: "map", // container ID
    style: MAP_STYLE, // style URL
    center: mapCenter, // starting position [lng, lat]
    zoom: mapZoom, // starting zoom
  });

  map.on("load", () => {
    map.addSource("LineString", {
      type: "geojson",
      data: geojson,
    });
    map.addLayer({
      id: "LineString",
      type: "line",
      source: "LineString",
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": MAP_LINE_COLOUR,
        "line-width": 5,
      },
    });

    // Geographic coordinates of the LineString
    const coordinates = geojson.features[0].geometry.coordinates;

    // Create a 'LngLatBounds' with both corners at the first coordinate.
    const bounds = new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]);

    // Extend the 'LngLatBounds' to include every coordinate in the bounds result.
    for (const coord of coordinates) {
      bounds.extend(coord);
    }

    map.fitBounds(bounds, {
      padding: 20,
    });

    // leaving the Mapbox credit, but removing the improve link
    // confirm this is okay by the mapbox TOS
    document.querySelector(".mapbox-improve-map").remove();
  });

  map.on("zoomend", () => {
    // set these so that when we re-render we don't bounce around
    mapZoom = map.getZoom();
    mapCenter = map.getCenter();
  });

  map.on("moveend", () => {
    // set these so that when we re-render we don't bounce around
    mapZoom = map.getZoom();
    mapCenter = map.getCenter();
  });
}

/*
    Stats at the top of the page
*/

function initStats() {
  console.log(SHOW_ELEVATION);
  function createStatDiv(name, value) {
    var stackedDiv = document.createElement("div");
    stackedDiv.className = "stacked";

    var statHeading = document.createElement("h4");
    statHeading.innerText = name;

    var statValue = document.createElement("p");
    statValue.innerText = value;

    stackedDiv.appendChild(statHeading);
    stackedDiv.appendChild(statValue);

    return stackedDiv;
  }

  /* Run fields */
  document.getElementById("name").innerText = run.name;

  let statsEl = document.getElementById("stats");
  statsEl.innerHTML = "";
  if (SHOW_DISTANCE)
    statsEl.appendChild(
      createStatDiv("Distance", run.distance.toFixed(1) + "km")
    );
  if (SHOW_DURATION)
    statsEl.appendChild(createStatDiv("Duration", toHHMMSS(run.duration)));
  if (SHOW_PACE)
    statsEl.appendChild(
      createStatDiv("Pace", toHHMMSS(run.duration / run.distance) + "/km")
    );
  if (SHOW_ELEVATION)
    statsEl.appendChild(
      createStatDiv("Elevation", run.uphill.toFixed(0) + "m")
    );
}

/*
Pace Chart!
*/

let chart;

function initChart() {
  if (chart) {
    chart.destroy();
  }

  let paceChartEl = document.getElementById("pace-chart");
  let title = document.getElementById("chart-title");
  let subTitle = document.getElementById("chart-subtitle");

  if (!SHOW_PACE_CHART) {
    paceChartEl.style.display = 'none';
    title.innerHTML = "";
    subTitle.innerHTML = "";
    return;
  } else {
    paceChartEl.style.display = 'block';
  }

  let clock_distance = zip([run.clock_values, run.distance_values]);
  let dist_per_duration = [];
  let next = CHART_SPLIT_DURATION;
  let prevDistance = 0;

  for (let value of clock_distance) {
    let clock = value[0];
    let distance = value[1];

    if (clock >= next) {
      dist_per_duration.push(distance - prevDistance);
      next += CHART_SPLIT_DURATION;
      prevDistance = distance;
    }
  }

  let chartData = dist_per_duration.map((el) => Math.floor(el * 1000));
  let chartMin = Math.floor(Math.min(...chartData) * 0.8);

  const ctx = document.getElementById("splits");
  ctx.style.height = "100px";
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: chartData.map((el, i) => i * CHART_SPLIT_DURATION),
      datasets: [
        {
          label: "Distance per 30 Seconds",
          data: chartData,
          borderWidth: 1,
          backgroundColor: CHART_COLOUR,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          display: false,
          suggestedMin: chartMin,
        },
        x: {
          display: false,
        },
      },
      plugins: {
        legend: {
          display: false,
        },
      },
    },
  });


  title.innerText = `Distance per ${CHART_SPLIT_DURATION} seconds`;

  let best_split = Math.max(...chartData);
  let best_pace = toHHMMSS(CHART_SPLIT_DURATION * (1000 / best_split));

  subTitle.innerText = `Best: ${best_pace} min/km`;
}

/*
Download PNG

"Get the canvas value immediately after rendering the map"

Two references here with code snippets that are combined to make this work:
https://github.com/mapbox/mapbox-gl-js/issues/2766#issuecomment-370758650
https://github.com/niklasvh/html2canvas/issues/2707#issuecomment-1003690418
*/

let downloadEl = document.querySelector("#download");
let runEl = document.querySelector(".run-wrapper");

function takeScreenshot(map) {
  return new Promise(function (resolve, reject) {
    map.once("render", function () {
      html2canvas(runEl, { scale: 2 }).then((canvas) => {
        url = canvas.toDataURL();
        resolve(url);
      });
    });

    /* trigger render */
    map.setBearing(map.getBearing());
  });
}

/*
    Init!
*/

function initAll() {
  initStats();
  initMap();
  initChart();

  downloadEl.onclick = () => {
    takeScreenshot(map).then(function (data) {
      window.open(data, "_blank").focus();
    });
  };
}

initAll();
