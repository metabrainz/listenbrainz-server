import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGear, faXmark } from "@fortawesome/free-solid-svg-icons";

function Sidebar(props: React.PropsWithChildren<{}>) {
  const { children } = props;

  const [isSidebarOpen, setIsSidebarOpen] = React.useState<boolean>(false);
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <>
      <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>{children}</div>
      <button
        className={`toggle-sidebar-button ${isSidebarOpen ? "open" : ""}`}
        onClick={toggleSidebar}
        type="button"
      >
        <FontAwesomeIcon icon={isSidebarOpen ? faXmark : faGear} size="2x" />
      </button>
      {isSidebarOpen && (
        <button
          className="sidebar-overlay"
          onClick={toggleSidebar}
          type="button"
        >
          {}
        </button>
      )}
    </>
  );
}

export default Sidebar;
