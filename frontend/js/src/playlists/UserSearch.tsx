import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { throttle as _throttle } from "lodash";
import { toast } from "react-toastify";
import debounceAsync from "debounce-async";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";
import { ToastMsg } from "../notifications/Notifications";

export type UserSearchProps = {
  onSelectUser: (userName: string) => void;
  placeholder: string;
  clearOnSelect?: boolean;
  initialValue?: string;
};

export type UserSearchState = {
  newUser: string;
  userSearchResults: Array<SearchUser>;
};

export default class UserSearch extends React.Component<
  UserSearchProps,
  UserSearchState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  // eslint-disable-next-line react/sort-comp
  constructor(props: UserSearchProps) {
    super(props);
    this.state = {
      newUser: props.initialValue ?? "",
      userSearchResults: [],
    };
  }

  throttledSearchUsers = _throttle(async () => {
    await this.searchUsers();
  }, 300);

  searchUsers = async () => {
    const { APIService } = this.context;
    const { newUser } = this.state;
    try {
      const response = await APIService.searchUsers(newUser);
      this.setState({
        userSearchResults: response.users,
      });
    } catch (error) {
      this.handleError(error);
    }
  };

  handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState(
      {
        newUser: event.target.value,
      },
      this.throttledSearchUsers
    );
  };

  handleResultClick = (user: string) => {
    const { onSelectUser, clearOnSelect } = this.props;
    onSelectUser(user);
    this.setState({
      newUser: clearOnSelect ? "" : user,
      userSearchResults: [],
    });
  };

  handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  render() {
    const { newUser, userSearchResults } = this.state;
    const { placeholder } = this.props;
    return (
      <>
        <input
          id="user-name-search"
          type="text"
          className="form-control"
          name="newUser"
          onChange={this.handleInputChange}
          placeholder={placeholder}
          value={newUser}
          aria-haspopup={Boolean(userSearchResults?.length)}
        />
        <div className="search-dropdown">
          {userSearchResults?.map((user) => {
            return (
              <ListenControl
                key={user.user_name}
                text={user.user_name}
                icon={faUser}
                // eslint-disable-next-line react/jsx-no-bind
                action={this.handleResultClick.bind(this, user.user_name)}
              />
            );
          })}
        </div>
      </>
    );
  }
}
