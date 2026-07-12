import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";

const NEED_TAGS = [
  { value: "mobility", label: "Mobility", detail: "Wheelchair, scooter, cane, walker, transfers", icon: "♿" },
  { value: "vision", label: "Blind / low vision", detail: "Guide help, accessible information", icon: "👁️" },
  { value: "hearing", label: "Deaf / hard of hearing", detail: "Visual communication, captions, alerts", icon: "🦻" },
  { value: "sensory", label: "Sensory needs", detail: "Autism, quiet help, reduced overwhelm", icon: "🧩" },
  { value: "cognitive", label: "Cognitive support", detail: "Plain instructions, extra guidance", icon: "📝" },
  { value: "service_animal", label: "Service animal", detail: "Service dog or other trained animal", icon: "🐕‍🦺" },
  { value: "medical", label: "Medical equipment", detail: "Medication, oxygen, CPAP, batteries", icon: "⚕️" },
  { value: "other", label: "Other accessibility need", detail: "Use when none of the other tags fit", icon: "＋" },
];

const TRANSPORT_OPTIONS = [
  { value: "not_sure", label: "Recommend for me", icon: "✨", detail: "Compare available modes" },
  { value: "air", label: "Flight", icon: "✈️", detail: "Airlines and airports" },
  { value: "rail", label: "Train", icon: "🚆", detail: "Amtrak and stations" },
  { value: "rideshare", label: "Taxi / rideshare", icon: "🚕", detail: "Local ride services" },
];

const DURATION_OPTIONS = [
  { id: "same_day", label: "Same day", days: 0.5, detail: "A few hours" },
  { id: "overnight", label: "Overnight", days: 2, detail: "1–2 days" },
  { id: "short_trip", label: "Short trip", days: 3, detail: "3 days" },
  { id: "week", label: "About a week", days: 7, detail: "4–7 days" },
  { id: "multi_day", label: "Longer trip", days: 10, detail: "8+ days" },
];

const DEFAULT_FORM = {
  quick_tags: [],
  transport_mode: "not_sure",
  duration_id: "short_trip",
  origin: null,
  destination: null,
  plain_language: true,
};

function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const resultHeadingRef = useRef(null);

  const selectedDuration = useMemo(
    () => DURATION_OPTIONS.find((option) => option.id === form.duration_id) || DURATION_OPTIONS[2],
    [form.duration_id],
  );
  const selectedMode = useMemo(
    () => TRANSPORT_OPTIONS.find((option) => option.value === form.transport_mode) || TRANSPORT_OPTIONS[0],
    [form.transport_mode],
  );

  const statusText = useMemo(() => {
    if (isSubmitting) return "Submitting your request.";
    if (jobStatus === "queued") return "Request queued.";
    if (jobStatus === "running") return "Checking provider accommodations.";
    if (jobStatus === "succeeded") return "Recommendation ready.";
    if (jobStatus === "failed") return "Recommendation failed.";
    return "";
  }, [isSubmitting, jobStatus]);

  useEffect(() => {
    if (!jobId || jobStatus === "succeeded" || jobStatus === "failed") {
      return undefined;
    }

    let isCancelled = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/recommend/${jobId}`);
        const data = await parseApiResponse(response);
        if (isCancelled) return;

        setJobStatus(data.status);
        setPollCount((count) => count + 1);

        if (data.status === "succeeded") {
          setResult(data.result);
          setError("");
          window.setTimeout(() => resultHeadingRef.current?.focus(), 0);
        } else if (data.status === "failed") {
          setError(data.error || "The recommendation request failed. Please retry.");
        } else if (data.status === "expired" || data.status === "not_found") {
          setJobStatus("failed");
          setError("This recommendation expired. Submit the form again.");
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setJobStatus("failed");
          setError(caughtError.message);
        }
      }
    }, pollCount === 0 ? 500 : 1500);

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [jobId, jobStatus, pollCount]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (form.quick_tags.length === 0) {
      setError("Select at least one accessibility need.");
      return;
    }
    if (!form.origin || !form.destination) {
      setError("Choose both an origin and a destination from the suggestions.");
      return;
    }

    setIsSubmitting(true);
    setJobId(null);
    setJobStatus("idle");
    setResult(null);
    setPollCount(0);

    const payload = {
      needs_description: buildNeedSummary(form.quick_tags),
      quick_tags: form.quick_tags,
      transport_modes: form.transport_mode === "not_sure" ? [] : [form.transport_mode],
      transport_preferences: selectedMode.label,
      trip_duration: selectedDuration.label,
      duration_days: selectedDuration.days,
      origin: form.origin,
      destination: form.destination,
      plain_language: form.plain_language,
    };

    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await parseApiResponse(response);
      setJobId(data.job_id);
      setJobStatus(data.status);
    } catch (caughtError) {
      setError(caughtError.message);
      setJobStatus("failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleTag(tag) {
    setForm((current) => {
      const hasTag = current.quick_tags.includes(tag);
      return {
        ...current,
        quick_tags: hasTag
          ? current.quick_tags.filter((item) => item !== tag)
          : [...current.quick_tags, tag],
      };
    });
  }

  function resetForm() {
    setForm(DEFAULT_FORM);
    setJobId(null);
    setJobStatus("idle");
    setResult(null);
    setError("");
    setPollCount(0);
  }

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="site-header">
        <div className="shell">
          <h1>Accessible Travel Assistant</h1>
          <p className="lede">
            Choose your needs, route, transportation preference, and trip length. The app
            ranks providers from a curated accessibility dataset and links to official
            policy and booking pages.
          </p>
        </div>
      </header>

      <main id="main-content" className="shell layout">
        <section className="panel" aria-labelledby="form-title">
          <h2 id="form-title">Plan your trip</h2>

          <form onSubmit={handleSubmit}>
            <fieldset className="tag-group">
              <legend>Accessibility needs</legend>
              <p className="helper" id="tag-help">
                Select all that apply. No medical explanation is required.
              </p>
              <div className="choice-grid" aria-describedby="tag-help">
                {NEED_TAGS.map((tag) => (
                  <button
                    className={`choice-card ${form.quick_tags.includes(tag.value) ? "selected" : ""}`}
                    key={tag.value}
                    type="button"
                    aria-pressed={form.quick_tags.includes(tag.value)}
                    onClick={() => toggleTag(tag.value)}
                  >
                    <span className="choice-icon" aria-hidden="true">
                      {tag.icon}
                    </span>
                    <span className="choice-title">{tag.label}</span>
                    <span className="choice-detail">{tag.detail}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset className="tag-group">
              <legend>Route</legend>
              <div className="route-grid">
                <LocationCombobox
                  id="origin"
                  label="Origin"
                  value={form.origin}
                  onChange={(location) => updateField("origin", location)}
                />
                <LocationCombobox
                  id="destination"
                  label="Destination"
                  value={form.destination}
                  onChange={(location) => updateField("destination", location)}
                />
              </div>
              <RouteMap origin={form.origin} destination={form.destination} />
            </fieldset>

            <fieldset className="tag-group">
              <legend>Transportation preference</legend>
              <div className="segmented-grid">
                {TRANSPORT_OPTIONS.map((option) => (
                  <button
                    className={`option-card ${form.transport_mode === option.value ? "selected" : ""}`}
                    key={option.value}
                    type="button"
                    aria-pressed={form.transport_mode === option.value}
                    onClick={() => updateField("transport_mode", option.value)}
                  >
                    <span className="choice-icon" aria-hidden="true">
                      {option.icon}
                    </span>
                    <span className="choice-title">{option.label}</span>
                    <span className="choice-detail">{option.detail}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset className="tag-group">
              <legend>Trip duration</legend>
              <div className="segmented-grid duration-grid">
                {DURATION_OPTIONS.map((option) => (
                  <button
                    className={`option-card ${form.duration_id === option.id ? "selected" : ""}`}
                    key={option.id}
                    type="button"
                    aria-pressed={form.duration_id === option.id}
                    onClick={() => updateField("duration_id", option.id)}
                  >
                    <span className="choice-title">{option.label}</span>
                    <span className="choice-detail">{option.detail}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={form.plain_language}
                onChange={(event) => updateField("plain_language", event.target.checked)}
              />
              <span>Use extra plain language in the explanation</span>
            </label>

            <div className="actions">
              <button
                className="primary"
                type="submit"
                disabled={isSubmitting || jobStatus === "running" || jobStatus === "queued"}
              >
                {isSubmitting || jobStatus === "running" || jobStatus === "queued"
                  ? "Working…"
                  : "Get recommendation"}
              </button>
              <button type="button" className="secondary" onClick={resetForm}>
                Clear
              </button>
            </div>
          </form>
        </section>

        <section className="panel results-panel" aria-labelledby="results-title">
          <h2 id="results-title" ref={resultHeadingRef} tabIndex="-1">
            Results
          </h2>
          <div className="status" role="status" aria-live="polite">
            {statusText}
          </div>

          {error && <ErrorMessage message={error} />}

          {!error && !result && (
            <div className="empty-state">
              <p>Results will appear here after you submit the form.</p>
              <p>
                The app may say “no strong match” if the curated dataset does not support
                the selected need well enough.
              </p>
            </div>
          )}

          {result && <RecommendationResult result={result} />}
        </section>
      </main>

      <footer className="shell site-footer">
        <p>
          Safety note: always confirm accommodations directly before booking. Provider
          policies and local service availability can change.
        </p>
      </footer>
    </>
  );
}

function LocationCombobox({ id, label, value, onChange }) {
  const [query, setQuery] = useState(value ? displayLocation(value) : "");
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const listboxId = `${id}-suggestions`;

  useEffect(() => {
    setQuery(value ? displayLocation(value) : "");
  }, [value]);

  useEffect(() => {
    let isCancelled = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/locations?q=${encodeURIComponent(query)}`);
        const data = await parseApiResponse(response);
        if (!isCancelled) {
          setSuggestions(data.locations || []);
        }
      } catch {
        if (!isCancelled) {
          setSuggestions([]);
        }
      }
    }, 150);

    return () => {
      isCancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [query]);

  function handleInput(event) {
    setQuery(event.target.value);
    setIsOpen(true);
    if (value) onChange(null);
  }

  function selectLocation(location) {
    onChange(location);
    setQuery(displayLocation(location));
    setIsOpen(false);
  }

  return (
    <div className="combobox">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="search"
        value={query}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        autoComplete="off"
        placeholder="Search city, airport code, or station"
        onChange={handleInput}
        onFocus={() => setIsOpen(true)}
        onBlur={() => window.setTimeout(() => setIsOpen(false), 160)}
      />
      {isOpen && suggestions.length > 0 && (
        <ul className="suggestions" id={listboxId} role="listbox">
          {suggestions.map((location) => (
            <li key={location.id} role="option" aria-selected={value?.id === location.id}>
              <button type="button" onMouseDown={() => selectLocation(location)}>
                <span className="suggestion-code">{location.code}</span>
                <span>
                  <strong>{location.city}, {location.state}</strong>
                  <small>{location.name}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RouteMap({ origin, destination }) {
  const mapElementRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  useEffect(() => {
    if (!mapElementRef.current || mapRef.current) return;

    mapRef.current = L.map(mapElementRef.current, {
      center: [39.5, -98.35],
      zoom: 4,
      scrollWheelZoom: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapRef.current);

    layerRef.current = L.layerGroup().addTo(mapRef.current);
  }, []);

  useEffect(() => {
    if (!mapRef.current || !layerRef.current) return;

    layerRef.current.clearLayers();
    const points = [origin, destination].filter(Boolean);

    points.forEach((point, index) => {
      L.marker([point.lat, point.lng], {
        title: `${index === 0 ? "Origin" : "Destination"}: ${displayLocation(point)}`,
        icon: L.divIcon({
          className: `route-marker ${index === 0 ? "origin-marker" : "destination-marker"}`,
          html: `<span>${index === 0 ? "A" : "B"}</span>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17],
        }),
      }).addTo(layerRef.current);
    });

    if (origin && destination) {
      const line = L.polyline(
        [
          [origin.lat, origin.lng],
          [destination.lat, destination.lng],
        ],
        { color: "#153e75", weight: 4, opacity: 0.8 },
      ).addTo(layerRef.current);
      mapRef.current.fitBounds(line.getBounds(), { padding: [42, 42], maxZoom: 6 });
    } else if (points.length === 1) {
      mapRef.current.setView([points[0].lat, points[0].lng], 7);
    } else {
      mapRef.current.setView([39.5, -98.35], 4);
    }
  }, [origin, destination]);

  return (
    <div className="map-card">
      <div
        ref={mapElementRef}
        className="route-map"
        aria-label="Interactive route map showing selected origin and destination"
      />
      <p className="map-helper">
        Pan or zoom the map. Search supports common US airport codes, city names, and a few
        major Amtrak stations.
      </p>
    </div>
  );
}

function RecommendationResult({ result }) {
  const isOk = result.status === "ok";

  return (
    <div className="recommendation">
      <div className={`result-banner ${isOk ? "ok" : "notice"}`}>
        <p className="status-label">Status: {humanizeStatus(result.status)}</p>
        <p>{result.summary}</p>
      </div>

      <dl className="summary-grid">
        <div>
          <dt>Detected needs</dt>
          <dd>{result.detected_needs?.length ? result.detected_needs.join(", ") : "Not clear"}</dd>
        </div>
        <div>
          <dt>Requested modes</dt>
          <dd>{result.requested_modes?.length ? result.requested_modes.join(", ") : "Not sure"}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>
            {result.duration?.raw || "Unknown"}{" "}
            {result.duration?.band ? `(${result.duration.band})` : ""}
          </dd>
        </div>
      </dl>

      {result.duration?.duration_considerations?.length > 0 && (
        <section aria-labelledby="duration-title">
          <h3 id="duration-title">Duration considerations</h3>
          <ul>
            {result.duration.duration_considerations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {isOk && result.providers?.length > 0 && (
        <section aria-labelledby="providers-title">
          <h3 id="providers-title">Recommended providers</h3>
          <div className="provider-list">
            {result.providers.map((provider) => (
              <ProviderCard provider={provider} key={provider.provider_id} />
            ))}
          </div>
        </section>
      )}

      {result.next_steps?.length > 0 && (
        <section aria-labelledby="next-steps-title">
          <h3 id="next-steps-title">Next steps</h3>
          <ol>
            {result.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      )}

      <p className="disclaimer">{result.disclaimer}</p>
    </div>
  );
}

function ProviderCard({ provider }) {
  return (
    <article className="provider-card">
      <div className="provider-heading">
        <img src={provider.logo_url} alt="" width="140" height="56" loading="lazy" />
        <div>
          <h4>{provider.provider_name}</h4>
          <p>
            {provider.mode} · Match score {provider.score}/100
          </p>
        </div>
      </div>

      {provider.why_recommended?.length > 0 && (
        <>
          <h5>Why this may fit</h5>
          <ul>
            {provider.why_recommended.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      )}

      {provider.watchouts?.length > 0 && (
        <>
          <h5>Check before booking</h5>
          <ul>
            {provider.watchouts.map((watchout) => (
              <li key={watchout}>{watchout}</li>
            ))}
          </ul>
        </>
      )}

      <div className="link-row">
        <a href={provider.policy_url} target="_blank" rel="noreferrer">
          Official accessibility policy
        </a>
        <a href={provider.booking_url} target="_blank" rel="noreferrer">
          Book or reserve
        </a>
      </div>
    </article>
  );
}

function ErrorMessage({ message }) {
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      <p>If this keeps happening, confirm the API key and try again later.</p>
    </div>
  );
}

async function parseApiResponse(response) {
  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const detail = data.detail;
    if (typeof detail === "string") {
      throw new Error(detail);
    }
    throw new Error("The request failed. Please retry.");
  }

  return data;
}

function buildNeedSummary(tags) {
  return tags
    .map((tag) => NEED_TAGS.find((item) => item.value === tag)?.label || tag)
    .join(", ");
}

function displayLocation(location) {
  if (!location) return "";
  return `${location.code} — ${location.city}, ${location.state}`;
}

function humanizeStatus(status) {
  return String(status || "unknown").replaceAll("_", " ");
}

export default App;
