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
  statusLabel?: string;
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
  statusLabel,
}: MusicServiceCardProps) {
  const isClickable = collapsible && onToggle;
  const shouldShowBody = collapsible ? isOpen : true;

  const headerContent = (
    <>
      <span className="service-logo">{icon}</span>
      <h3 className="card-title">{title}</h3>
      {showStatusIndicator && (
        <div className="status-indicator">
          <div
            className={`status-dot ${
              isConnected ? "connected" : "disconnected"
            }`}
          />
          <span>{statusLabel ?? (isConnected ? "Connected" : "Not Connected")}</span>
        </div>
      )}
    </>
  );

  return (
    <div className="card">
      {isClickable ? (
        <div
          className="card-header"
          role="button"
          tabIndex={0}
          onClick={onToggle}
          onKeyDown={(e) => e.key === "Enter" && onToggle?.()}
          style={{ cursor: "pointer" }}
        >
          {headerContent}
        </div>
      ) : (
        <div className="card-header">{headerContent}</div>
      )}
      {shouldShowBody && <div className="card-body">{children}</div>}
    </div>
  );
}
