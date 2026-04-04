import "./Loader.css";

export default function Loader({ text = "Loading...", fullPage = false }) {
  const content = (
    <div className="loader-container">
      <div className="loader-spinner">
        <div className="loader-ring" />
        <div className="loader-icon">🤖</div>
      </div>
      <div className="loader-text">{text}</div>
      <div className="loader-dots">
        <span /><span /><span />
      </div>
    </div>
  );

  if (fullPage) {
    return <div className="loader-fullpage">{content}</div>;
  }
  return content;
}
