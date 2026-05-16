import { init } from "./ui";

describe("ui init", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("sets capped card stagger indexes without NodeList callback iteration", () => {
    document.body.innerHTML = `
      <div class="filter-bar-wrapper"></div>
      ${Array.from({ length: 17 }, (_, index) => `<div class="ioc-card" data-index="${index}"></div>`).join("")}
    `;

    const forEachSpy = vi.spyOn(NodeList.prototype, "forEach").mockImplementation(() => {
      throw new Error("card stagger setup should use indexed iteration");
    });

    init();

    const cards = document.querySelectorAll<HTMLElement>(".ioc-card");
    expect(forEachSpy).not.toHaveBeenCalled();
    expect(cards[0].style.getPropertyValue("--card-index")).toBe("0");
    expect(cards[14].style.getPropertyValue("--card-index")).toBe("14");
    expect(cards[15].style.getPropertyValue("--card-index")).toBe("15");
    expect(cards[16].style.getPropertyValue("--card-index")).toBe("15");
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
