from pathlib import Path

from PIL import Image


def main() -> None:
    #print(type(__file__))
    #print(dir(__file__))
    #print(__file__)
    o = Path(__file__)
    #print(type(o))
    #print(dir(o))
    #print(o)
    image_path = Path(__file__).with_name("shutterstock_432248797-1024x683.jpg")
    image = Image.open(image_path)
    width, height = image.size
    resized_image = image.resize((max(1, width // 2), max(1, height // 2)))
    #print(image)
    #print(type(image))
    #print(dir(image))
    resized_image.show()


if __name__ == "__main__":
    main()
