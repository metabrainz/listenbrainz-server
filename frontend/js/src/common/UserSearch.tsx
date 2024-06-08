import * as React from "react";
import { throttle as _throttle } from "lodash";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

export type UserSearchProps = {
  onSelectUser: (userName: string) => void;
  placeholder: string;
  clearOnSelect?: boolean;
  initialValue?: string;
};

export default function UserSearch(props: UserSearchProps) {
  // Context
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { onSelectUser, placeholder, clearOnSelect, initialValue } = props;

  // States
  const [newUser, setNewUser] = React.useState(initialValue ?? "");
  const [userSearchResults, setUserSearchResults] = React.useState<
    Array<SearchUser>
  >([]);
  const [selectedIndex, setSelectedIndex] = React.useState(-1);

  // Refs
  const dropdownRef = React.useRef<HTMLSelectElement>(null);

  const searchUsers = async () => {
    try {
      const response = await APIService.searchUsers(newUser);
      setUserSearchResults(response.users);
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "error",
      });
    }
  };

  const throttledSearchUsers = _throttle(async () => {
    await searchUsers();
  }, 300);

  const handleResultClick = (user: string) => {
    onSelectUser(user);
    setNewUser(clearOnSelect ? "" : user);
    setUserSearchResults([]);
  };

  const reset = () => {
    setUserSearchResults([]);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      setSelectedIndex((prevIndex) =>
        prevIndex < userSearchResults.length - 1 ? prevIndex + 1 : prevIndex
      );
    } else if (event.key === "ArrowUp") {
      setSelectedIndex((prevIndex) =>
        prevIndex > 0 ? prevIndex - 1 : prevIndex
      );
    } else if (event.key === "Enter" && selectedIndex >= 0) {
      handleResultClick(userSearchResults[selectedIndex].user_name);
      reset();
    }
  };

  React.useEffect(() => {
    if (!newUser) {
      return;
    }
    throttledSearchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newUser]);

  React.useEffect(() => {
    if (selectedIndex >= 0 && dropdownRef.current) {
      const option = dropdownRef.current.options[selectedIndex];
      option.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  return (
    <div
      className="input-group user-search"
      style={{
        width: "100%",
      }}
    >
      <input
        id="user-name-search"
        type="text"
        className="form-control"
        name="newUser"
        onChange={(event) => {
          setNewUser(event.target.value);
        }}
        placeholder={placeholder}
        value={newUser}
        aria-haspopup={Boolean(userSearchResults?.length)}
        onKeyDown={handleKeyDown}
      />
      {Boolean(userSearchResults?.length) && (
        <select
          className="user-search-dropdown"
          size={Math.min(userSearchResults.length, 8)}
          onChange={(e) => {
            handleResultClick(e.target.value);
          }}
          tabIndex={-1}
          ref={dropdownRef}
          onKeyDown={handleKeyDown}
          style={{
            width: "100%",
          }}
        >
          {userSearchResults?.map((user, index) => {
            return (
              <option
                key={user.user_name}
                value={user.user_name}
                style={
                  index === selectedIndex
                    ? { backgroundColor: "#353070", color: "white" }
                    : {}
                }
                aria-selected={index === selectedIndex}
              >
                {user.user_name}
              </option>
            );
          })}
        </select>
      )}
    </div>
  );
}
