from scripts import get_s2_data, get_gcc_data, generate_map, get_temp_data

def main():
    get_temp_data.run()
    get_s2_data.run()
    get_gcc_data.run()
    generate_map.run()

if __name__ == "__main__":
    main()
    