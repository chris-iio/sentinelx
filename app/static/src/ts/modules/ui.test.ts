import { init } from "./ui";

describe("ui init", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("only toggles the scrolled class when the threshold state changes", () => {
    document.body.innerHTML = `<div class="filter-bar-wrapper"></div>`;

    init();

    const filterBar = document.querySelector<HTMLElement>(".filter-bar-wrapper")!;
    const scrollY = vi.spyOn(window, "scrollY", "get").mockReturnValue(50);
    window.dispatchEvent(new Event("scroll"));
    window.dispatchEvent(new Event("scroll"));

    expect(filterBar.classList.contains("is-scrolled")).toBe(true);

    scrollY.mockReturnValue(0);
    window.dispatchEvent(new Event("scroll"));

    expect(filterBar.classList.contains("is-scrolled")).toBe(false);
  });
});
