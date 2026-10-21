import * as React from "react";
import { Accordion } from "react-bootstrap";

interface MusicServiceCardProps {
  serviceId: string;
  icon: React.ReactNode;
  title: string;
  isConnected?: boolean;
  children?: React.ReactNode;
  collapsible?: boolean;
  statusLabel?: string;
}

export default function MusicServiceCard({
  serviceId,
  icon,
  title,
  isConnected = false,
  children,
  collapsible = true,
  statusLabel,
}: MusicServiceCardProps) {
  const bodyId = `music-service-${serviceId}-body`;

  const headerContent = (
    <>
      <span className="service-logo">{icon}</span>
      <span className="card-title">{title}</span>
      <span className="status-indicator">
        <span
          className={`status-dot ${isConnected ? "connected" : "disconnected"}`}
        />
        <span>
          {statusLabel ?? (isConnected ? "Connected" : "Not Connected")}
        </span>
      </span>
    </>
  );

  if (!collapsible) {
    return (
      <div className="card">
        <h3 className="card-header mb-0">{headerContent}</h3>
        <div className="card-body">{children}</div>
      </div>
    );
  }

  return (
    <Accordion.Item eventKey={serviceId} bsPrefix="card">
      <Accordion.Header as="div" aria-controls={bodyId}>
        {headerContent}
      </Accordion.Header>
      <Accordion.Collapse
        eventKey={serviceId}
        id={bodyId}
        mountOnEnter
        unmountOnExit
      >
        <div className="card-body">{children}</div>
      </Accordion.Collapse>
    </Accordion.Item>
  );
}
