import * as React from "react";

interface MusicServiceCardProps {
  serviceId: string;
  icon: React.ReactNode;
  title: string;
  isConnected: boolean;
  isOpen: boolean;
  onToggle: () => void;
  children?: React.ReactNode;
}

export default function MusicServiceCard({
  serviceId,
  icon,
  title,
  isConnected,
  isOpen,
  onToggle,
  children,
}: MusicServiceCardProps) {
  return (
    <div className="card">
      <div
        className="card-header"
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(e) => e.key === "Enter" && onToggle()}
        style={{ cursor: "pointer" }}
      >
        <span className="service-logo">{icon}</span>

        <h3 className="card-title">{title}</h3>
        <div className="status-indicator">
          <div
            className={`status-dot ${
              isConnected ? "connected" : "disconnected"
            }`}
          />
          <span>{isConnected ? "Connected" : "Not Connected"}</span>
        </div>
      </div>
      {isOpen && <div className="card-body">{children}</div>}
    </div>
  );
}
