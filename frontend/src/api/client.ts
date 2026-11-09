/** 后端 HTTP 客户端、会话代次隔离及图书字段适配。 */
import type { Book, BookInput, Role, Session } from "../stores/library";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const TOKEN_KEY = "qingye.access_token";
let requestGeneration = 0;

export class ApiError extends Error {
  /** 保存 message 错误说明与 status HTTP 状态，网络错误使用 0。 */
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class RequestCancelled extends ApiError {
  /** 表示所属会话或查询已失效，消费者应忽略此结果；无参数。 */
  constructor() {
    super("", 0);
    this.name = "RequestCancelled";
  }
}

/** 判断 error 是否为明确失效的请求，页面无需展示该错误。 */
export function isRequestCancelled(error: unknown): error is RequestCancelled {
  return error instanceof RequestCancelled;
}

/** 使所有在途请求失效，不修改当前令牌；无参数。 */
export function invalidateRequests(): void {
  requestGeneration++;
}

/** 检查 generation 是否仍属于当前会话。 */
function assertCurrent(generation: number): void {
  if (generation !== requestGeneration) throw new RequestCancelled();
}

interface Envelope<T> {
  code: number;
  msg: string;
  data: T;
}
interface ApiBook {
  id: number;
  name: string;
  price: number;
  author: string | null;
  category: string | null;
  description: string | null;
  cover: string;
  created_at: string;
  published_at: string | null;
  published: boolean;
  file?: { name: string; format: "TXT"; size: number; url: string } | null;
}
interface ApiUser {
  id: number;
  username: string;
  name: string;
  role: Role;
}
export interface PageResult {
  list: Book[];
  total: number;
  page: number;
  pageSize: number;
}
export interface OverviewResult {
  bookCount: number;
  downloadableCount: number;
  favoriteCount: number;
  latestBooks: Book[];
  recommendation: Book | null;
}

/** 将后端 book 转为前端字段，可空历史文字交由界面展示缺失状态。 */
function mapBook(book: ApiBook): Book {
  return {
    id: String(book.id),
    name: book.name,
    price: book.price,
    author: book.author ?? "",
    category: book.category ?? "",
    description: book.description ?? "",
    cover: book.cover,
    createdAt: book.created_at,
    publishedAt: book.published_at ?? undefined,
    published: book.published,
    file: book.file ?? undefined,
  };
}

/** 将后端 user 转为公开会话资料。 */
function mapUser(user: ApiUser): Session {
  return {
    id: String(user.id),
    username: user.username,
    name: user.name,
    role: user.role,
  };
}

/** 用 path、init 发送真实请求，generation 防止旧会话继续处理响应。 */
async function fetchResponse(
  path: string,
  init: RequestInit,
  generation: number,
): Promise<Response> {
  assertCurrent(generation);
  const headers = new Headers(init.headers);
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body instanceof URLSearchParams) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
  } else if (
    init.body &&
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
    assertCurrent(generation);
    return response;
  } catch (error) {
    assertCurrent(generation);
    if (error instanceof TypeError)
      throw new ApiError("无法连接后端服务，请检查服务后重试。", 0);
    throw error;
  }
}

/** 读取 response JSON；generation 隔离旧会话，区分网络中断和无效内容。 */
async function readEnvelope<T>(
  response: Response,
  generation: number,
): Promise<Envelope<T>> {
  try {
    const body = (await response.json()) as Envelope<T>;
    assertCurrent(generation);
    return body;
  } catch (error) {
    assertCurrent(generation);
    if (error instanceof TypeError)
      throw new ApiError("读取响应时连接中断，请重试。", 0);
    if (error instanceof SyntaxError) {
      throw new ApiError(
        response.ok
          ? "服务器返回了无效响应"
          : `请求失败（HTTP ${response.status}）`,
        response.status,
      );
    }
    throw error;
  }
}

/** 请求 path 的 JSON 接口，init 为 HTTP 配置，仅返回有效会话的 data。 */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const generation = requestGeneration;
  const response = await fetchResponse(path, init, generation);
  const body = await readEnvelope<T>(response, generation);
  if (!response.ok || body.code !== 200) {
    throw new ApiError(
      body.msg || `请求失败（HTTP ${response.status}）`,
      response.status,
    );
  }
  return body.data;
}

/** 为已知 error 返回页面消息；失效请求返回空串，其余异常保留原始错误。 */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  throw error;
}

/** 用 account、password 表单登录，仅当前会话可以保存返回令牌。 */
export async function login(
  account: string,
  password: string,
): Promise<Session> {
  const generation = requestGeneration;
  const result = await request<{
    access_token: string;
    token_type: string;
    user: ApiUser;
  }>("/auth/token", {
    method: "POST",
    body: new URLSearchParams({ username: account, password }),
  });
  assertCurrent(generation);
  sessionStorage.setItem(TOKEN_KEY, result.access_token);
  return mapUser(result.user);
}

/** 返回当前令牌对应的真实用户；无参数。 */
export async function currentUser(): Promise<Session> {
  return mapUser(await request<ApiUser>("/auth/me"));
}

/** 请求服务端撤销当前令牌；无参数。 */
export function logout(): Promise<null> {
  return request<null>("/auth/logout", { method: "POST" });
}

/** 清除当前标签页令牌；无参数。 */
export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

/** 按 params 查询服务端书目分页。 */
export async function listBooks(params: {
  q?: string;
  category?: string;
  sort?: string;
  page: number;
  pageSize: number;
  scope?: "all";
}): Promise<PageResult> {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.q) query.set("q", params.q);
  if (params.category) query.set("category", params.category);
  if (params.sort) query.set("sort", params.sort);
  if (params.scope) query.set("scope", params.scope);
  const result = await request<{
    list: ApiBook[];
    total: number;
    page: number;
    page_size: number;
  }>(`/books?${query}`);
  return {
    list: result.list.map(mapBook),
    total: result.total,
    page: result.page,
    pageSize: result.page_size,
  };
}

/** 查询已上架分类；无参数。 */
export function listCategories(): Promise<string[]> {
  return request<string[]>("/books/categories");
}

/** 查询已上架图书 id。 */
export async function getBook(id: string): Promise<Book> {
  return mapBook(await request<ApiBook>(`/books/${encodeURIComponent(id)}`));
}

/** 获取当前用户的真实概览；无参数。 */
export async function getOverview(): Promise<OverviewResult> {
  const data = await request<{
    book_count: number;
    downloadable_count: number;
    favorite_count: number;
    latest_books: ApiBook[];
    recommendation: ApiBook | null;
  }>("/overview");
  return {
    bookCount: data.book_count,
    downloadableCount: data.downloadable_count,
    favoriteCount: data.favorite_count,
    latestBooks: data.latest_books.map(mapBook),
    recommendation: data.recommendation ? mapBook(data.recommendation) : null,
  };
}

/** 获取当前用户的全部可见收藏；无参数。 */
export async function listFavorites(): Promise<Book[]> {
  return (await request<ApiBook[]>("/favorites")).map(mapBook);
}

/** 保存 input 完整资料，id 省略时创建新书。 */
export function saveBook(input: BookInput, id?: string): Promise<ApiBook> {
  const body = JSON.stringify({
    name: input.name.trim(),
    price: input.price,
    author: input.author.trim(),
    category: input.category.trim(),
    description: input.description.trim(),
    cover: input.cover,
    published: input.published,
  });
  return request<ApiBook>(id ? `/books/${encodeURIComponent(id)}` : "/books", {
    method: id ? "PUT" : "POST",
    body,
  });
}

/** 将图书 id 的上架状态设为 published。 */
export function setPublished(id: string, published: boolean): Promise<ApiBook> {
  return request<ApiBook>(`/books/${encodeURIComponent(id)}/publication`, {
    method: "PATCH",
    body: JSON.stringify({ published }),
  });
}

/** 删除图书 id。 */
export function deleteBook(id: string): Promise<null> {
  return request<null>(`/books/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/** 将当前用户对 id 的收藏状态设为 favorite。 */
export function setFavorite(id: string, favorite: boolean): Promise<null> {
  return request<null>(`/favorites/${encodeURIComponent(id)}`, {
    method: favorite ? "PUT" : "DELETE",
  });
}

/** 使用真实 Bearer 请求图书 id 的文件，网络、401及失效语义与 JSON 一致。 */
export async function downloadFile(id: string): Promise<Blob> {
  const generation = requestGeneration;
  const response = await fetchResponse(
    `/books/${encodeURIComponent(id)}/download`,
    {},
    generation,
  );
  if (!response.ok) {
    const body = await readEnvelope<unknown>(response, generation);
    throw new ApiError(
      body.msg || `下载失败（HTTP ${response.status}）`,
      response.status,
    );
  }
  try {
    const blob = await response.blob();
    assertCurrent(generation);
    return blob;
  } catch (error) {
    assertCurrent(generation);
    if (error instanceof TypeError)
      throw new ApiError("下载时连接中断，请重试。", 0);
    throw error;
  }
}
