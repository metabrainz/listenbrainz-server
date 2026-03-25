import * as React from "react";

interface MusicServiceCardProps {
  serviceId: string;
  icon: React.ReactNode;
  title: string;
  isConnected?: boolean;
  isOpen?: boolean;
  onToggle?: () => void;
  children?: React.ReactNode;
  collapsible?: boolean;
  showStatusIndicator?: boolean;
}

export default function MusicServiceCard({
  serviceId,
  icon,
  title,
  isConnected = false,
  isOpen = false,
  onToggle,
  children,
  collapsible = true,
  showStatusIndicator = true,
}: MusicServiceCardProps) {
  const isClickable = collapsible && onToggle;
  const shouldShowBody = collapsible ? isOpen : true;

  return (
    <div className="card">
      <div
        className="card-header"
        role={isClickable ? "button" : undefined}
        tabIndex={isClickable ? 0 : undefined}
        onClick={isClickable ? onToggle : undefined}
        onKeyDown={
          isClickable ? (e) => e.key === "Enter" && onToggle?.() : undefined
        }
        style={{ cursor: isClickable ? "pointer" : "default" }}
      >
        <span className="service-logo">{icon}</span>

        <h3 className="card-title">{title}</h3>
        {showStatusIndicator && (
          <div className="status-indicator">
            <div
              className={`status-dot ${
                isConnected ? "connected" : "disconnected"
              }`}
            />
            <span>{isConnected ? "Connected" : "Not Connected"}</span>
          </div>
        )}
      </div>
      {shouldShowBody && <div className="card-body">{children}</div>}
    </div>
  );
}
