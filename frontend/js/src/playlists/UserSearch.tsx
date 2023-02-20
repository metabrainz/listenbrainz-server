import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { throttle as _throttle } from "lodash";
import debounceAsync from "debounce-async";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";

export type UserSearchProps = {
  onSelectUser: (userName: string) => void;
  placeholder: string;
} & WithAlertNotificationsInjectedProps;

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
      newUser: "",
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
    const { onSelectUser } = this.props;
    onSelectUser(user);
    this.setState({
      newUser: "",
      userSearchResults: [],
    });
  };

  handleError = (error: any) => {
    const { newAlert } = this.props;
    newAlert("danger", "Error", error.message);
  };

  render() {
    const { newUser, userSearchResults } = this.state;
    const { placeholder } = this.props;
    return (
      <div>
        <input
          type="text"
          className="form-control"
          name="newUser"
          onChange={this.handleInputChange}
          placeholder={placeholder}
          value={newUser}
        />
        <div className="search-dropdown">
          {userSearchResults?.map((user) => {
            return (
              <ListenControl
                text={`${user.user_name}`}
                icon={faUser}
                // eslint-disable-next-line react/jsx-no-bind
                action={this.handleResultClick.bind(this, user.user_name)}
              />
            );
          })}
        </div>
      </div>
    );
  }
}
