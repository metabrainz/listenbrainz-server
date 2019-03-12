import {isFinite, isNil, isString} from 'lodash';

export default class APIService {
  
  APIBaseURI;

  constructor(APIBaseURI){
    if(isNil(APIBaseURI) || !isString(APIBaseURI)){
      throw new SyntaxError(`Expected API base URI string, got ${typeof APIBaseURI} instead`)
    }
    if(APIBaseURI.endsWith('/')){
      APIBaseURI = APIBaseURI.substring(0, APIBaseURI.length-1);
    }
    if(!APIBaseURI.endsWith('/1')){
      APIBaseURI += '/1';
    }
    this.APIBaseURI = APIBaseURI;
  }

  async getRecentListensForUsers(userNames, limit) {
    let userNamesForQuery = userNames;
    if (Array.isArray(userNames)){
      userNamesForQuery = userNames.join(',');
    }
    else if(typeof userNames !== 'string') {
      throw new SyntaxError(`Expected username or array of username strings, got ${typeof userNames} instead`);
    }

    let query = `${this.APIBaseURI}/users/${userNamesForQuery}/recent-listens`;

    if(!isNil(limit) && isFinite(Number(limit))){
      query += `?limit=${limit}`
    }
    
    const response = await fetch(query, {
      accept: 'application/json',
      method: "GET"
    })
    this.checkStatus(response);
    const result = await response.json();
    
    return result.payload.listens
  }
  
  async getListensForUser(userName, minTs, maxTs, count) {
    
    if(typeof userName !== 'string'){
      throw new SyntaxError(`Expected username string, got ${typeof userName} instead`);
    }
    if(!isNil(maxTs) && !isNil(minTs)) {
      throw new SyntaxError('Cannot have both minTs and maxTs defined at the same time');
    }

    let query = `${this.APIBaseURI}/user/${userName}/listens`;

    const queryParams = [];
    if(!isNil(maxTs) && isFinite(Number(maxTs))){
      queryParams.push(`max_ts=${maxTs}`)
    }
    if(!isNil(minTs) && isFinite(Number(minTs))){
      queryParams.push(`min_ts=${minTs}`)
    }
    if(!isNil(count) && isFinite(Number(count))){
      queryParams.push(`count=${count}`)
    }
    if(queryParams.length) {
      query += `?${queryParams.join("&")}`
    }

    const response = await fetch(query, {
      accept: 'application/json',
      method: "GET"
    })
    this.checkStatus(response);
    const result = await response.json();
    
    return result.payload.listens
  }

  async refreshSpotifyToken(){
    const response = await fetch("/profile/refresh-spotify-token",{method:"POST"})
    this.checkStatus(response);
    const result = await response.json();
    return result.user_token;
  }
  
  checkStatus(response) {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    const error = new Error(`HTTP Error ${response.statusText}`);
    error.status = response.statusText;
    error.response = response;
    throw error;
  }
}