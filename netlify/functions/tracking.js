const { connectLambda, getStore } = require("@netlify/blobs");

const DEFAULT_STATE = {
  version: "1.0",
  last_updated: null,
  properties: {},
  favorites: [],
  visits: [],
  discarded: [],
  notes: {}
};

exports.handler = async (event, context) => {
  const headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers, body: "" };
  }

  try {
    // Connect the blobs client to the environment using the Lambda event
    if (typeof connectLambda === 'function') {
      connectLambda(event);
    }

    const store = getStore("barranquilla_rentals");

    // 1. GET Request: Read shared state
    if (event.httpMethod === "GET") {
      let state = await store.get("tracking", { type: "json" });
      if (!state || typeof state !== "object" || Array.isArray(state)) {
        state = DEFAULT_STATE;
      }
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify(state)
      };
    }

    // 2. POST Request: Merge and persist shared state
    if (event.httpMethod === "POST") {
      const body = JSON.parse(event.body || "{}");
      let current = await store.get("tracking", { type: "json" });
      if (!current || typeof current !== "object" || Array.isArray(current) || !current.properties) {
        current = JSON.parse(JSON.stringify(DEFAULT_STATE));
      }

      if (body.property_id) {
        const pid = body.property_id;
        current.properties[pid] = {
          ...(current.properties[pid] || {}),
          ...body,
          updated_at: new Date().toISOString()
        };
      } else if (body.properties && typeof body.properties === "object") {
        current = {
          ...current,
          ...body,
          properties: { ...current.properties, ...body.properties }
        };
      }

      // Re-index helper arrays
      const props = current.properties || {};
      current.favorites = Object.keys(props).filter(id => props[id].favorite || props[id].status === 'favorito');
      current.discarded = Object.keys(props).filter(id => props[id].status === 'descartado');
      current.visits = Object.keys(props).filter(id => props[id].status === 'visita_programada');
      current.last_updated = new Date().toISOString();

      await store.setJSON("tracking", current);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true, data: current })
      };
    }

    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: "Method not allowed" })
    };
  } catch (err) {
    console.error("Tracking function error:", err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message || "Internal server error" })
    };
  }
};
